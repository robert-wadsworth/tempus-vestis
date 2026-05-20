import pytest
from unittest.mock import MagicMock, patch

from langchain_core.documents import Document

from core.rag import (
    WardrobeRAG,
    _CHUNK_SIZE,
    get_or_create_vectorstore,
    load_wardrobe_knowledge,
)


class TestLoadWardrobeKnowledge:
    def test_returns_documents(self):
        docs = load_wardrobe_knowledge()
        assert isinstance(docs, list)
        assert len(docs) > 0
        assert all(isinstance(d, Document) for d in docs)

    def test_chunks_within_size_limit(self):
        docs = load_wardrobe_knowledge()
        # Allow a small buffer — splitter may slightly exceed chunk_size at boundaries
        for doc in docs:
            assert len(doc.page_content) <= _CHUNK_SIZE * 1.5

    def test_raises_on_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_wardrobe_knowledge("/nonexistent/path/rules.txt")


class TestGetOrCreateVectorstore:
    @patch('core.rag.FAISS')
    @patch('core.rag._build_embeddings')
    @patch('core.rag.Path')
    def test_loads_from_disk_when_path_exists(self, mock_path_cls, mock_build_emb, mock_faiss):
        mock_path_cls.return_value.exists.return_value = True
        mock_embeddings = MagicMock()
        mock_build_emb.return_value = mock_embeddings
        mock_vs = MagicMock()
        mock_faiss.load_local.return_value = mock_vs

        result = get_or_create_vectorstore()

        mock_faiss.load_local.assert_called_once()
        assert result is mock_vs

    @patch('core.rag.FAISS')
    @patch('core.rag._build_embeddings')
    @patch('core.rag.Path')
    def test_builds_and_saves_when_no_path(self, mock_path_cls, mock_build_emb, mock_faiss):
        mock_path_cls.return_value.exists.return_value = False
        mock_embeddings = MagicMock()
        mock_build_emb.return_value = mock_embeddings
        mock_vs = MagicMock()
        mock_faiss.from_documents.return_value = mock_vs

        docs = [Document(page_content="test content")]
        result = get_or_create_vectorstore(documents=docs)

        mock_faiss.from_documents.assert_called_once_with(docs, mock_embeddings)
        mock_vs.save_local.assert_called_once()
        assert result is mock_vs


class TestWardrobeRAG:
    def _make_rag(self, mock_vs: MagicMock) -> WardrobeRAG:
        """Construct a WardrobeRAG with vectorstore and chain mocked out."""
        with patch('core.rag.get_or_create_vectorstore', return_value=mock_vs):
            with patch('core.rag.create_wardrobe_rag_chain', return_value=MagicMock()):
                return WardrobeRAG()

    def test_search_knowledge_returns_documents(self):
        expected = [Document(page_content="Pack a light jacket below 60°F")]
        mock_vs = MagicMock()
        mock_vs.as_retriever.return_value.invoke.return_value = expected

        rag = self._make_rag(mock_vs)
        results = rag.search_knowledge("cold weather packing")

        assert results == expected
        assert all(isinstance(d, Document) for d in results)

    def test_search_knowledge_respects_k(self):
        mock_vs = MagicMock()
        mock_vs.as_retriever.return_value.invoke.return_value = []

        rag = self._make_rag(mock_vs)
        rag.search_knowledge("query", k=2)

        mock_vs.as_retriever.assert_called_with(search_kwargs={"k": 2})

    def test_format_weather_info_passthrough_for_string(self):
        mock_vs = MagicMock()
        rag = self._make_rag(mock_vs)
        result = rag._format_weather_info("Sunny, 72°F")
        assert result == "Sunny, 72°F"

    def test_format_weather_info_formats_nws_dict(self):
        mock_vs = MagicMock()
        rag = self._make_rag(mock_vs)
        weather = {
            "properties": {
                "periods": [{
                    "name": "Today",
                    "temperature": 72,
                    "temperatureUnit": "F",
                    "shortForecast": "Sunny",
                    "windSpeed": "10 mph",
                }]
            }
        }
        result = rag._format_weather_info(weather)
        assert "72" in result
        assert "Sunny" in result
        assert "Today" in result
