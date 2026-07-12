from abc import ABC, abstractmethod


class PythonAnalysisPort(ABC):
    @abstractmethod
    def analyze_chunks(self, chunks: list[dict], analysis_type: str) -> dict: ...
