import os
import uvicorn
import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager

# LangChain 相关的导入
from langchain.chains import RetrievalQA
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
# 从 google 导入 LLM 和 Embedding 类
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma

# --- 1. 全局配置 ---

# Gemini 配置 (用于 LLM 和 Embedding)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# RAG/文件配置
PDF_PATH = "my_document.pdf"
# 更改持久化目录名称，以区分旧的 DeepSeek 数据库
PERSIST_DIRECTORY = 'chroma_db_gemini_native'


# --- 2. 数据模型 (Pydantic) ---

class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[str]


# --- 3. Lifespan 上下文管理器 ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    RAG 链的生命周期事件处理器：启动时初始化 RAG 链。
    """
    print("--- RAG Lifespan: 启动初始化中 ---")

    # 检查 Gemini API Key
    if not GEMINI_API_KEY:
        print("FATAL: GEMINI_API_KEY 环境变量未设置！服务将无法工作。", file=sys.stderr)
        app.state.qa_chain = None
        yield;
        return

    try:
        # 1. 配置 LLM (Gemini 模型)
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0,
            google_api_key=GEMINI_API_KEY
        )

        # 2. 配置 Embedding Model (Google Native Embedding)
        embeddings = GoogleGenerativeAIEmbeddings(
            model="text-embedding-004",  # Google 推荐的最新嵌入模型
            google_api_key=GEMINI_API_KEY
        )
        print("Gemini LLM 和 Google Native Embedding 模型配置完成。")

        # 3. 检查并加载/创建向量数据库
        # 注意：如果目录存在但里面的数据是用 DeepSeek 创建的，程序仍会失败。
        # 最佳做法是，如果更换了 Embedding 模型，就删除旧的 PERSIST_DIRECTORY 文件夹。
        if os.path.exists(PERSIST_DIRECTORY):
            print(f"检测到现有向量数据库，正在加载...")
            vectordb = Chroma(persist_directory=PERSIST_DIRECTORY, embedding_function=embeddings)
        else:
            print(f"未找到向量数据库，正在从 {PDF_PATH} 创建新的数据库...")

            if not os.path.exists(PDF_PATH):
                raise FileNotFoundError(f"未找到 PDF 文件：{PDF_PATH}。请放置文件后重新启动。")

            # 加载、分割、嵌入
            loader = PyPDFLoader(PDF_PATH)
            documents = loader.load()
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            texts = text_splitter.split_documents(documents)

            vectordb = Chroma.from_documents(
                documents=texts,
                embedding=embeddings,
                persist_directory=PERSIST_DIRECTORY
            )
            print(f"向量数据库创建并持久化完成。包含 {len(texts)} 个文本块。")

        # 4. 创建 QA 链并存储在 app.state 中
        base_retriever = vectordb.as_retriever(search_kwargs={"k": 3})

        app.state.qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=base_retriever,
            return_source_documents=True
        )
        print("RAG 链初始化成功。服务已准备就绪。")

    except Exception as e:
        print(f"RAG 初始化失败: {e}", file=sys.stderr)
        app.state.qa_chain = None

    yield

    # --- 关闭逻辑 ---
    print("--- RAG Lifespan: 服务关闭中 ---")
    if hasattr(app.state, 'qa_chain'):
        app.state.qa_chain = None
    print("服务清理完成。")


# --- 4. FastAPI 应用实例 ---

app = FastAPI(
    title="Gemini Native RAG 服务",
    description="基于 Gemini 模型的完全原生本地文档问答 API。",
    lifespan=lifespan
)


# --- 5. API 路由定义 ---

@app.get("/")
async def health_check():
    """健康检查接口，检查服务是否运行和RAG是否初始化。"""
    if hasattr(app.state, 'qa_chain') and app.state.qa_chain:
        return {"status": "ok", "message": "Gemini Native RAG Service is ready."}
    else:
        raise HTTPException(status_code=503,
                            detail="RAG Service not initialized. Check server logs for API Key errors.")


@app.post("/query", response_model=QueryResponse)
async def handle_query(request: QueryRequest):
    """
    处理用户查询，运行 RAG 问答链。
    """
    qa_chain = getattr(app.state, 'qa_chain', None)

    if not qa_chain:
        raise HTTPException(status_code=503, detail="RAG 问答服务尚未初始化。")

    try:
        # 运行问答链
        result = qa_chain.invoke({"query": request.query})

        # 格式化溯源信息
        sources_list = []
        for doc in result['source_documents']:
            source_info = f"{doc.metadata.get('source', 'Unknown File')} (页码: {doc.metadata.get('page', 'N/A')})"
            sources_list.append(source_info)

        return QueryResponse(
            answer=result['result'],
            sources=list(set(sources_list))
        )

    except Exception as e:
        print(f"原始错误类型: {type(e)}", file=sys.stderr)
        print(f"处理查询时发生原始错误: {e}", file=sys.stderr)

        raise HTTPException(status_code=500, detail=f"查询失败，请检查 Gemini API 或网络连接。")


# --- 6. 启动服务 ---

if __name__ == "__main__":
    # 使用 Uvicorn 启动服务
    uvicorn.run(app, host="0.0.0.0", port=8000)