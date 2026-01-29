import os
from fastapi import HTTPException, UploadFile
from unstructured.partition.pdf import partition_pdf
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.runnables import RunnablePassthrough

from config import embeddings, groq_llm, ollama_llm
from prompts import strict_pdf_prompt
from utils import setup_environment_paths

vectorstore = None
retriever = None
docs_loaded = False

setup_environment_paths()


async def upload_files(files: list[UploadFile]):
    global vectorstore, retriever, docs_loaded

    documents = []

    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files supported")

        temp_path = f"temp_{file.filename}"
        with open(temp_path, "wb") as f:
            f.write(await file.read())

        try:
            elements = partition_pdf(
                filename=temp_path,
                strategy="hi_res",           # OCR for scanned PDFs
                infer_table_structure=True,  # Tables
                extract_images_in_pdf=False,
                languages=["eng"]
            )

            for el in elements:
                text = str(el).strip()
                if not text:
                    continue

                # ✅ FIXED LINE (NO .get())
                page = getattr(el.metadata, "page_number", "Unknown")

                documents.append(
                    Document(
                        page_content=text,
                        metadata={
                            "page": page,
                            "source": file.filename
                        }
                    )
                )

        finally:
            os.remove(temp_path)

    if not documents:
        return {"status": "No extractable content found"}

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    docs = splitter.split_documents(documents)

    vectorstore = Chroma.from_documents(docs, embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 20})
    docs_loaded = True

    return {"status": "PDF indexed successfully"}


async def get_chat_response(query: str, online: bool):
    global retriever, docs_loaded, vectorstore

    if not docs_loaded:
        return "No PDF uploaded."

    llm = groq_llm if online else ollama_llm

    # 1️⃣ Semantic retrieval (NEW LANGCHAIN API)
    docs = retriever.invoke(query)

    # 2️⃣ Keyword fallback (for headings like Session 6)
    if not docs:
        all_docs = vectorstore.similarity_search("", k=50)
        query_lower = query.lower()

        docs = [
            d for d in all_docs
            if query_lower in d.page_content.lower()
        ]

    # 3️⃣ Strict rejection
    if not docs:
        return "The specified concept is not present in the uploaded PDF."

    # 4️⃣ Build strict context with page reference
    context = "\n\n".join(
        f"(Page {d.metadata.get('page', 'Unknown')}) {d.page_content}"
        for d in docs
    )

    # 5️⃣ Strict PDF-only answer
    chain = strict_pdf_prompt | llm
    return chain.invoke(
        {"context": context, "question": query}
    ).content

