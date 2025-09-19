from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
from langchain.chains import RetrievalQA
from langgraph.prebuilt import create_react_agent


@tool
def duckduckgo_search(query: str) -> str:
    """Performs a web search using DuckDuckGo and returns results."""
    return DuckDuckGoSearchRun().run(query)


loader = TextLoader("company_knowledge.txt")
docs = loader.load()

embeddings = OllamaEmbeddings(model="embeddinggemma")
vectorstore = FAISS.from_documents(docs, embeddings)

@tool
def knowledgebase_qa(query: str) -> str:
    """Performs knowledge-base search"""
    chain = RetrievalQA.from_chain_type(
        llm=ChatOllama(model="orieg/gemma3-tools:1b"),
        chain_type="stuff",
        retriever=vectorstore.as_retriever()
    )
    return chain.run(query)

tools = [duckduckgo_search, knowledgebase_qa]

llm = ChatOllama(model="orieg/gemma3-tools:1b", temperature=0.2)

agent = create_react_agent(llm, tools)

query = "Who is the current president of India?"
response = agent.invoke({"messages": [{"role": "user", "content": query}]})
print(response["messages"][-1].content)
