import os
import logging
from typing import Dict, Any, List
from sentence_transformers import SentenceTransformer
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from src.database import DatabaseHelper

logger = logging.getLogger(__name__)

MODEL_NAME = os.environ.get("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

class RAGService:
    def __init__(self, db_helper: DatabaseHelper):
        self.db_helper = db_helper
        logger.info(f"Loading query embedding model: {MODEL_NAME}")
        self.encoder = SentenceTransformer(MODEL_NAME)
        
        # Initialize LangChain prompt template
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are an enterprise AI assistant. Answer the user's question using ONLY the provided context. If the answer cannot be found in the context, say 'I cannot find the answer in the provided documents.' Do not make things up.\n\nContext:\n{context}"),
            ("user", "Question: {question}")
        ])

    def query(self, question: str, limit: int = 4) -> Dict[str, Any]:
        """
        Embeds the query, retrieves matching chunks from the DB,
        and generates an answer using LangChain and OpenAI (or a helpful mock).
        """
        # 1. Embed query
        logger.info(f"Embedding query: '{question}'")
        query_vector = self.encoder.encode(question).tolist()

        # 2. Retrieve top chunks from pgvector database
        logger.info(f"Retrieving top {limit} matches from pgvector...")
        similar_chunks = self.db_helper.query_similar_chunks(query_vector, limit=limit)
        
        if not similar_chunks:
            return {
                "question": question,
                "answer": "No relevant documents found. Please ingest some PDF files first.",
                "sources": [],
                "mode": "offline-empty"
            }

        # 3. Format context and extract sources
        context_parts = []
        sources = []
        for idx, chunk in enumerate(similar_chunks):
            doc_name = chunk["document_name"]
            page = chunk["metadata"].get("page", "Unknown")
            content = chunk["text_content"]
            similarity = chunk["similarity_score"]
            
            context_parts.append(f"--- Document: {doc_name} | Page: {page} ---\n{content}\n")
            
            sources.append({
                "document_name": doc_name,
                "page": page,
                "similarity_score": similarity,
                "snippet": content[:150] + "..." if len(content) > 150 else content
            })

        context_str = "\n".join(context_parts)

        # 4. Generate answer using LLM
        if OPENAI_API_KEY:
            logger.info("Generating response using OpenAI via LangChain...")
            try:
                llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.0, openai_api_key=OPENAI_API_KEY)
                chain = self.prompt_template | llm
                response = chain.invoke({
                    "context": context_str,
                    "question": question
                })
                answer = response.content
                mode = "openai"
            except Exception as e:
                logger.error(f"Failed to query OpenAI: {e}")
                answer = f"Error querying OpenAI: {e}. Falling back to offline context extraction."
                mode = "error-fallback"
        else:
            logger.info("No OpenAI key configured. Generating a simulated response for local testing.")
            # Build a mock response that demonstrates the correct context is retrieved
            top_source = sources[0]
            answer = (
                f"[OFFLINE MOCK RESPONSE] OpenAI API Key is not configured. "
                f"The vector search successfully retrieved {len(sources)} matching chunk(s) from the pgvector database.\n\n"
                f"Top Document Match:\n- File: {top_source['document_name']}\n- Page: {top_source['page']}\n"
                f"- Similarity Score: {top_source['similarity_score']}\n\n"
                f"Retrieved Content snippet:\n\"{top_source['snippet']}\"\n\n"
                f"To get live generative answers, populate the OPENAI_API_KEY environment variable."
            )
            mode = "offline-mock"

        return {
            "question": question,
            "answer": answer,
            "sources": sources,
            "mode": mode
        }
