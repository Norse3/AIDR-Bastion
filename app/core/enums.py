from enum import Enum, strEnum


class PipelineNames(str, Enum):
    llm = "llm"
    ml = "ml"
    code_analysis = "code_analysis"
    rule = "rule"
    similarity = "similarity"


class ActionStatus(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    NOTIFY = "notify"
    ERROR = "error"


class PipelineLabel(str, Enum):
    CLEAR = "clear"


class Language(str, Enum):
    C = "c"
    CPP = "cpp"
    CSHARP = "csharp"
    GOLANG = "golang"
    HACK = "hack"
    JAVA = "java"
    JAVASCRIPT = "javascript"
    KOTLIN = "kotlin"
    PHP = "php"
    PYTHON = "python"
    RUBY = "ruby"
    RUST = "rust"
    SWIFT = "swift"
    LANGUAGE_AGNOSTIC = "language_agnostic"

    def __str__(self) -> str:
        return self.name.lower()


class RuleAction(str, Enum):
    NOTIFY = "notify"
    BLOCK = "block"


class SimilarityClientNames(strEnum):
    opensearch = "opensearch"
    elasticsearch = "elasticsearch"


class LLMClientNames(strEnum):
    openai = "openai"
    deepseek = "deepseek"
    anthropic = "anthropic"
    google = "google"
    azure = "azure"
    ollama = "ollama"
    groq = "groq"
    mistral = "mistral"
    gemini = "gemini"


class ManagerNames(strEnum):
    similarity = "similarity"
    llm = "llm"
