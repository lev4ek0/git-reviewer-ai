from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from pathlib import Path

from ml.code_analyzer import CodeAnalyzer
from ml.files_parser import FilesParser
from ml.layer_classifier import LayerClassifier
from ml.logging_checker import LoggingChecker
from ml.project_structure_analyzer import ProjectStructureAnalyzer
from ml.reqs_match import ReqsMatcher
from ml.schemas import CodeComment, OutputJson, ProjectComment

DATA_PATH = r"D:\ITMO\hacks\llm_review\python\backend-master"
# DATA_PATH = r'/home/artem/work/programming/codereview_hack/example_projects/python/backend-master/backend-master'


type_to_title = {
    "reqs_match": "Недопустимые зависимости",
    "project_structure": "Недочеты в структуре проекта",
    "architecture": "Архитектурные ошибки",
    "logging": "Логирование",
    "auth": "Аутентификация и авторизация",
    "data": "Работа с данными",
}


class CodeReviewer:
    def __init__(
        self,
        files_parser: FilesParser,
        layer_classifier: LayerClassifier,
        project_structure_analyzer: ProjectStructureAnalyzer,
        reqs_matcher: ReqsMatcher,
        scripts_validators: list = [],
    ):
        self.files_parser = files_parser
        self.layer_classifier = layer_classifier
        self.project_structure_analyzer = project_structure_analyzer
        self.reqs_matcher = reqs_matcher
        self.scripts_validators = scripts_validators

    def _postprocess_result(self, results, path_to_file: str):
        output_results = []
        for result in results:
            output_results += [
                CodeComment(
                    title=type_to_title[x.type],
                    filepath=str(path_to_file),
                    start_string_number=x.start_line_number,
                    end_string_number=x.end_line_number,
                    comment=x.comment,
                    suggestion=(
                        str(x.suggestion)
                        if hasattr(x, "suggestion") and x.suggestion
                        else None
                    ),
                )
                for x in result.comments
            ]
        return output_results

    def _process_py_file(
        self, source_dir: Path, relative_path: Path, layer_name: str = None
    ):
        with open(source_dir / relative_path, "r") as f:
            contents = f.read()

        results = []
        for validator in self.scripts_validators:
            if isinstance(validator, CodeAnalyzer):
                result = validator.invoke(contents, layer_name, str(relative_path))
            else:
                result = validator.invoke(contents)
            results.append(result)

        return self._postprocess_result(results, relative_path)

    def invoke(self, source_dir: Path, extension: str = ".py"):
        if isinstance(source_dir, str):
            source_dir = Path(source_dir)

        if len(os.listdir(source_dir)) == 1 and os.listdir(source_dir)[0].endswith(".py"):
            source_dir = Path(os.path.join(source_dir, os.listdir(source_dir)[0]))

        if source_dir.is_file():
            try:
                result = self._process_py_file(Path(""), source_dir)
                result = [x for x in result if x.title != "Архитектурные ошибки"]
            except:
                result = []
            return OutputJson(
                titles=list(type_to_title.values()),
                code_comments=result,
                project_comments=[],
            )

        project_structure = self.files_parser.invoke(source_dir, extension=extension)
        reqs = self.reqs_matcher.invoke(source_dir)
        classes = self.layer_classifier.invoke(project_structure)

        project_structure_analyzer_results = self.project_structure_analyzer.invoke(
            source_dir
        )
        project_comments = [
            ProjectComment(title=type_to_title[x.type], comment=x.comment)
            for x in project_structure_analyzer_results.comments
        ]

        if reqs:
            project_comments.append(
                ProjectComment(title=type_to_title[reqs.type], comment=reqs.comment)
            )

        project_structure = {k: project_structure[k] for k in classes}
        scripts = [
            (path / x, classes[path])
            for path in project_structure
            for x in project_structure[path]
        ]
        code_comments = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_sc = {
                executor.submit(
                    self._process_py_file, source_dir, script[0], script[1]
                ): script[0]
                for script in scripts
            }
            for future in as_completed(future_to_sc):
                script_name = future_to_sc[future]
                try:
                    data = future.result()
                    code_comments += data
                except Exception as exc:
                    print(f"{script_name} сгенерировано исключение: {exc}")

        return OutputJson(
            titles=list(type_to_title.values()),
            code_comments=code_comments,
            project_comments=project_comments,
        )


if __name__ == "__main__":
    from ml.llms import LLMFactory

    llm = LLMFactory.get_llm("mistral-nemo-instruct-2407")

    reviewer = CodeReviewer(
        FilesParser(),
        LayerClassifier(llm),
        ProjectStructureAnalyzer(llm),
        ReqsMatcher(),
        scripts_validators=[CodeAnalyzer(llm), LoggingChecker(llm)],
    )
    EXTENSION = ".py"
    result = reviewer.invoke(DATA_PATH, EXTENSION)
    print(result)

    with open("output1.json", "w", encoding="utf-8") as f:
        import json

        json.dump(result.model_dump(), f, indent=4, ensure_ascii=False)
