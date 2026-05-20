"""RAG (Retrieval-Augmented Generation) implementation for wardrobe knowledge."""

import os
from pathlib import Path
from typing import Any

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Number of knowledge-base chunks retrieved per query.
# 4 gives enough context for temperature + activity rules without exceeding
# the prompt budget for gpt-4o-mini.
RETRIEVAL_K = 4

# Matches the agent temperature — keeps recommendations specific rather than
# drifting into generic suggestions.
LLM_TEMPERATURE = 0.7

_VECTORSTORE_PATH = "data/vectorstore"
_CHUNK_SIZE = 500
_CHUNK_OVERLAP = 100


def load_wardrobe_knowledge(file_path: str | None = None) -> list[Document]:
    """Load and chunk the wardrobe rules knowledge base."""
    if file_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        file_path = os.path.join(base_dir, "data", "wardrobe_rules.txt")

    with open(file_path) as f:
        content = f.read()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=_CHUNK_SIZE,
        chunk_overlap=_CHUNK_OVERLAP,
    )
    return splitter.create_documents([content])


def _build_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=os.getenv("OPENAI_API_KEY"),
    )


def get_or_create_vectorstore(
    documents: list[Document] | None = None,
) -> FAISS:
    """Load the FAISS index from disk if it exists, otherwise build and save it."""
    embeddings = _build_embeddings()

    if Path(_VECTORSTORE_PATH).exists():
        return FAISS.load_local(
            _VECTORSTORE_PATH,
            embeddings,
            allow_dangerous_deserialization=True,
        )

    if documents is None:
        documents = load_wardrobe_knowledge()

    vectorstore = FAISS.from_documents(documents, embeddings)
    vectorstore.save_local(_VECTORSTORE_PATH)
    return vectorstore


def create_wardrobe_rag_chain(
    vectorstore: FAISS | None = None,
    model_name: str = "gpt-4o-mini",
    temperature: float = LLM_TEMPERATURE,
    k: int = RETRIEVAL_K,
):
    """Create a RAG chain for wardrobe recommendations."""
    if vectorstore is None:
        vectorstore = get_or_create_vectorstore()

    retriever = vectorstore.as_retriever(search_kwargs={"k": k})

    llm = ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    template = """You are a wardrobe and packing expert. Use the following wardrobe knowledge to provide specific, actionable recommendations.

Weather Information:
{weather_info}

Relevant Wardrobe Guidelines:
{context}

User Query: {question}

Provide a detailed, practical packing list and wardrobe recommendations based on the weather and the wardrobe guidelines. Be specific about clothing items, accessories, and quantities."""

    prompt = ChatPromptTemplate.from_template(template)

    def format_docs(docs: list[Document]) -> str:
        return "\n\n".join(doc.page_content for doc in docs)

    def create_rag_input(input_data: dict[str, Any]) -> dict[str, Any]:
        docs = retriever.invoke(input_data["question"])
        return {
            "context": format_docs(docs),
            "question": input_data["question"],
            "weather_info": input_data["weather_info"],
        }

    return create_rag_input | prompt | llm | StrOutputParser()


class WardrobeRAG:
    """Wrapper around the wardrobe RAG chain."""

    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        temperature: float = LLM_TEMPERATURE,
        k: int = RETRIEVAL_K,
    ) -> None:
        self.vectorstore = get_or_create_vectorstore()
        self.chain = create_wardrobe_rag_chain(
            vectorstore=self.vectorstore,
            model_name=model_name,
            temperature=temperature,
            k=k,
        )

    def get_recommendations(self, query: str, weather_info: Any) -> str:
        """Return wardrobe recommendations for the given query and weather data."""
        return self.chain.invoke({
            "question": query,
            "weather_info": self._format_weather_info(weather_info),
        })

    def _format_weather_info(self, weather_info: Any) -> str:
        """Format weather data into a readable string for the prompt."""
        if isinstance(weather_info, str):
            return weather_info

        formatted = "Weather Forecast:\n"
        if "properties" in weather_info:
            for period in weather_info["properties"].get("periods", [])[:7]:
                formatted += (
                    f"\n{period.get('name', 'Unknown')}:\n"
                    f"  Temperature: {period.get('temperature', 'N/A')}°{period.get('temperatureUnit', 'F')}\n"
                    f"  Conditions: {period.get('shortForecast', 'N/A')}\n"
                    f"  Wind: {period.get('windSpeed', 'N/A')}\n"
                )
        else:
            formatted += str(weather_info)

        return formatted

    def search_knowledge(self, query: str, k: int = RETRIEVAL_K) -> list[Document]:
        """Search the wardrobe knowledge base and return relevant chunks."""
        return self.vectorstore.as_retriever(search_kwargs={"k": k}).invoke(query)
