from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from layer_classifier import LayerClassifier 
from files_parser import FilesParser
from code_layer_matcher import CodeLayerMatcher, CodeLayerMatchResult
from logging_checker import LoggingChecker, ListLoggingCheckerOutput
from reqs_match import ReqsMatcher
from schemas import OutputJson, ProjectComment, CodeComment


DATA_PATH = r"D:\ITMO\hacks\llm_review\python\backend-master\alembic"


type_to_title = {
    CodeLayerMatchResult: "Архитектурные ошибки",
    ListLoggingCheckerOutput: "Логирование",
    str: "Недопустимые зависимости"
}


class CodeReviewer:
    def __init__(
        self,
        files_parser: FilesParser,
        layer_classifier: LayerClassifier,
        reqs_matcher: ReqsMatcher,
        scripts_validators: list = [],
    ):
        self.files_parser = files_parser
        self.layer_classifier = layer_classifier
        self.reqs_matcher = reqs_matcher
        self.scripts_validators = scripts_validators

    def _postprocess_result(self, results, path_to_file: str):
        output_results = []
        for result in results:
            output_results += [
                CodeComment(title=type_to_title[type(result)],
                            filepath=str(path_to_file),
                            start_string_number=x.start_line_number,
                            end_string_number=x.end_line_number,
                            comment=x.comment,
                            suggestion=str(x.suggestion) if hasattr(x, "suggestion") and x.suggestion else None) 
                for x in result.comments
            ]
        return output_results

    def _process_py_file(self, source_dir: Path, relative_path: Path, layer_name: str = None):
        with open(source_dir / relative_path, "r") as f:
            contents = f.read()

        results = []
        for validator in self.scripts_validators:
            if isinstance(validator, CodeLayerMatcher):
                
                result = validator.invoke(contents, layer_name, str(relative_path))
            else:
                result = validator.invoke(contents)
            results.append(result)
        
        return self._postprocess_result(results, source_dir / relative_path)

    def invoke(self, source_dir: Path):
        if isinstance(source_dir, str):
            source_dir = Path(source_dir)

        if source_dir.is_file():
            return self._process_py_file(Path(""), source_dir)
        
        project_structure = self.files_parser.invoke(source_dir)
        reqs = self.reqs_matcher.invoke(source_dir)
        classes = self.layer_classifier.invoke(project_structure)
        project_comments = []
        if reqs:
            project_comments.append(ProjectComment(title=type_to_title[type(reqs)], comment=reqs))

        project_structure = {k: project_structure[k] for k in classes}
        scripts = [(path / x, classes[path]) for path in project_structure for x in project_structure[path]]
        code_comments = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_sc = {executor.submit(self._process_py_file, source_dir, script[0], script[1]): script[0]
                            for script in scripts}
            for future in as_completed(future_to_sc):
                script_name = future_to_sc[future]
                try:
                    data = future.result()
                    code_comments += data
                except Exception as exc:
                    print(f'{script_name} сгенерировано исключение: {exc}')

        return OutputJson(titles=list(type_to_title.values()), code_comments=code_comments, project_comments=project_comments)


if __name__ == "__main__":
    from llms import LLMFactory
    llm = LLMFactory.get_llm("Qwen/Qwen2.5-Coder-32B-Instruct")

    reviewer = CodeReviewer(FilesParser(), LayerClassifier(llm), ReqsMatcher(),
                            scripts_validators=[CodeLayerMatcher(llm), LoggingChecker(llm)])
    result = reviewer.invoke(DATA_PATH)
    print(result)

    with open("output.json", "w", encoding="utf-8") as f:
        import json
        json.dump(result.model_dump(), f, indent=4, ensure_ascii=False)
