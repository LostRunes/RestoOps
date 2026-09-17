import re


class TemplateEngine:
    def render(self, template: str | None, context: dict[str, str | None]) -> str:
        if not template:
            return ""

        def replacer(match: re.Match) -> str:
            var_name = match.group(1).strip()
            val = context.get(var_name)
            if val is not None:
                return str(val)
            return ""

        # Matches {{ variable_name }}
        pattern = r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}"
        return re.sub(pattern, replacer, template)
