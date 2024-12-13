"""
title: Haystack Pipeline
author: open-webui
date: 2024-05-30
version: 1.0
license: MIT
description: A pipeline for retrieving relevant information from a knowledge base using the Haystack library.
requirements: haystack-ai, datasets>=2.6.1, sentence-transformers>=2.2.0
"""

from typing import List, Union, Generator, Iterator
from schemas import OpenAIChatMessage
import os
import asyncio


class Pipeline:
    def __init__(self):
        self.basic_rag_pipeline = None

    async def on_startup(self):
        from haystack.components.retrievers import InMemoryBM25Retriever
        from haystack.components.builders import PromptBuilder
        from haystack_integrations.components.generators.ollama import OllamaGenerator

        from haystack.document_stores.in_memory import InMemoryDocumentStore

        from datasets import load_dataset
        from haystack import Document
        from haystack import Pipeline

        document_store = InMemoryDocumentStore()

        dataset = load_dataset("bilgeyucel/seven-wonders", split="train")
        docs = [Document(content=doc["content"], meta=doc["meta"]) for doc in dataset]

        doc_embedder = SentenceTransformersDocumentEmbedder(
            model="sentence-transformers/all-MiniLM-L6-v2", token=Secret.from_token("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")
        )
        doc_embedder.warm_up()

        docs_with_embeddings = doc_embedder.run(docs)
        document_store.write_documents(docs_with_embeddings["documents"])

        text_embedder = SentenceTransformersTextEmbedder(
            model="sentence-transformers/all-MiniLM-L6-v2", token=Secret.from_token("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")
        )

        retriever = InMemoryEmbeddingRetriever(document_store)

        template = """
        Given the following information, answer the question.

        Context:
        {% for document in documents %}
            {{ document.content }}
        {% endfor %}

        Question: {{question}}
        Answer:
        """

        prompt_builder = PromptBuilder(template=template)

        generator = OllamaGenerator(model="Llama-3.2-Test-Finetune:latest", url="http://localhost:11434")

        self.basic_rag_pipeline = Pipeline()
        # Add components to your pipeline
        self.basic_rag_pipeline.add_component("text_embedder", text_embedder)
        self.basic_rag_pipeline.add_component("retriever", retriever)
        self.basic_rag_pipeline.add_component("prompt_builder", prompt_builder)
        self.basic_rag_pipeline.add_component("llm", generator)

        # Now, connect the components to each other
        self.basic_rag_pipeline.connect(
            "text_embedder.embedding", "retriever.query_embedding"
        )
        self.basic_rag_pipeline.connect("retriever", "prompt_builder.documents")
        self.basic_rag_pipeline.connect("prompt_builder", "llm")

        pass

    async def on_shutdown(self):
        # This function is called when the server is stopped.
        pass

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        # This is where you can add your custom RAG pipeline.
        # Typically, you would retrieve relevant information from your knowledge base and synthesize it to generate a response.

        print(messages)
        print(user_message)

        question = user_message
        response = self.basic_rag_pipeline.run(
            {
                "text_embedder": {"text": question},
                "prompt_builder": {"question": question},
            }
        )

        return response["llm"]["replies"][0]
