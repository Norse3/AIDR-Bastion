import asyncio
import json
import os
import tempfile
from pathlib import Path

from app.core.dataclasses import SemgrepLangConfig
from app.core.enums import ActionStatus, Language, PipelineNames, RuleAction
from app.models.pipeline import PipelineResult, TriggeredRuleData
from app.modules.logger import bastion_logger
from app.pipelines.base import BasePipeline


class CodeAnalysisPipeline(BasePipeline):
    """
    Semgrep-based pipeline for static code analysis of programming languages.

    This pipeline uses Semgrep to perform static analysis on code snippets
    in various programming languages. It supports multiple languages and
    can detect security vulnerabilities, code quality issues, and other
    patterns defined in Semgrep rules.

    Attributes:
        name (PipelineNames): Pipeline name (code)
        enabled (bool): Always enabled pipeline
        _languages_data_map (dict): Mapping of languages to Semgrep configurations
    """

    name = PipelineNames.code_analysis
    enabled = True

    _languages_data_map: dict[Language, SemgrepLangConfig] = {
        Language.C: SemgrepLangConfig(config_name="p/c", file_extension=".c"),
        Language.CPP: SemgrepLangConfig(config_name="p/c", file_extension=".c"),
        Language.CSHARP: SemgrepLangConfig(config_name="p/csharp", file_extension=".cs"),
        Language.HACK: SemgrepLangConfig(config_name="p/php", file_extension=".php"),
        Language.JAVA: SemgrepLangConfig(config_name="p/java", file_extension=".java"),
        Language.JAVASCRIPT: SemgrepLangConfig(config_name="p/javascript", file_extension=".js"),
        Language.KOTLIN: SemgrepLangConfig(config_name="p/kotlin", file_extension=".kt"),
        Language.PHP: SemgrepLangConfig(config_name="p/php", file_extension=".php"),
        Language.PYTHON: SemgrepLangConfig(config_name="p/python", file_extension=".py"),
        Language.RUBY: SemgrepLangConfig(config_name="p/ruby", file_extension=".rb"),
        Language.RUST: SemgrepLangConfig(config_name="p/rust", file_extension=".rs"),
        Language.SWIFT: SemgrepLangConfig(config_name="p/swift", file_extension=".swift"),
    }

    def __init__(self):
        super().__init__()
        bastion_logger.info(
            f"[{self}] loaded successfully. Languages: {', '.join([lang.value for lang in self._languages_data_map.keys()])}"
        )

    def _get_semgrep_local_rules_dir(self, language: str) -> str | None:
        """
        Gets local Semgrep rules directory for specific language.

        Checks if a local rules directory exists for the specified language
        and returns its path if found.

        Args:
            language (str): Programming language name

        Returns:
            str | None: Path to local rules directory or None if not found
        """
        rules_dir_path = f"{Path(__file__).parent}/rules/semgrep/{language}"
        if os.path.exists(rules_dir_path) and os.path.isdir(rules_dir_path):
            return rules_dir_path

    async def run(self, prompt: str, **kwargs) -> PipelineResult:
        """
        Analyzes code prompt using Semgrep static analysis.

        Performs static code analysis on the provided prompt using Semgrep
        for the specified programming language. Returns scan results with
        triggered rules if any issues are found.

        Args:
            prompt (str): Code prompt to analyze
            **kwargs: Additional keyword arguments, including 'language'

        Returns:
            PipelineResult: Analysis result with triggered rules and status
        """
        language = kwargs.get("language", "")
        bastion_logger.info(f"Analyzing for language: {language}")
        triggered_rule_data = await self._scan_for_language(prompt, language)
        status = ActionStatus.BLOCK if triggered_rule_data else ActionStatus.ALLOW
        bastion_logger.info(f"Analyzing for language: {language}, status: {status}")
        return PipelineResult(name=str(self), triggered_rules=triggered_rule_data, status=status)

    async def _scan_for_language(self, prompt: str, language: Language) -> list[TriggeredRuleData]:
        """
        Performs Semgrep analysis for specific programming language.

        Creates a temporary file with the code prompt and runs Semgrep
        analysis using language-specific configurations and rules.

        Args:
            prompt (str): Code content to analyze
            language (Language): Programming language for analysis

        Returns:
            list[TriggeredRuleData]: List of triggered rules from Semgrep analysis
        """
        triggered_rule_data = []
        if not (lang_config_data := self._languages_data_map.get(language)):
            return triggered_rule_data

        cmd = ["semgrep", "scan", "--metrics=off"]
        if lang_config_data.config_name:
            cmd.append(f"--config={lang_config_data.config_name}")
        if rules_dir := self._get_semgrep_local_rules_dir(language.value):
            cmd.append(f"--config={rules_dir}")

        if not (lang_config_data.config_name or rules_dir):
            return triggered_rule_data

        tmp_file_path = ""
        try:
            with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=lang_config_data.file_extension) as file:
                file.write(prompt)
                tmp_file_path = file.name

            cmd.extend(["--json", tmp_file_path])
            result = await self._run_semgrep_task(cmd)
            processed = self._process_semgrep_analysis_result(result)
            triggered_rule_data.extend(processed)
        finally:
            if tmp_file_path:
                os.unlink(tmp_file_path)

            return triggered_rule_data

    @staticmethod
    def _process_semgrep_analysis_result(result: dict) -> list[TriggeredRuleData]:
        """
        Processes Semgrep analysis results and converts to TriggeredRuleData.

        Parses the JSON output from Semgrep and extracts relevant information
        to create TriggeredRuleData objects for each detected issue.

        Args:
            result (dict): JSON result from Semgrep analysis

        Returns:
            list[TriggeredRuleData]: List of triggered rules from analysis results
        """
        triggered_rule_data = []
        for triggered in result.get("results", []):
            extra = triggered.get("extra", {})
            triggered_rule_data.append(
                TriggeredRuleData(
                    details=extra.get("message", ""),
                    severity=extra.get("severity", "").lower(),
                    cwe_id=extra.get("metadata", {}).get("cwe_id", "").lower(),
                    action=RuleAction.BLOCK,
                )
            )

        return triggered_rule_data

    @staticmethod
    async def _run_semgrep_task(cmd: list[str]) -> dict:
        """
        Executes Semgrep command asynchronously and returns JSON result.

        Runs the Semgrep command as a subprocess and captures its output.
        Returns parsed JSON result or empty dict on failure.

        Args:
            cmd (list[str]): Semgrep command and arguments to execute

        Returns:
            dict: Parsed JSON result from Semgrep or empty dict on error
        """
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            return {}

        return json.loads(stdout.decode())
