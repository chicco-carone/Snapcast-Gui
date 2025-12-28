import html
import re


class LogHighlighter:
    """
    A utility class for highlighting log messages with HTML formatting based on line-level keywords.
    """

    LINE_COLORS = {
        "error": ("#dc3545", 4),  # Red - highest priority
        "fail": ("#dc3545", 4),  # Red
        "failed": ("#dc3545", 4),  # Red
        "exception": ("#dc3545", 4),  # Red
        "warning": ("#fd7e14", 3),  # Orange
        "warn": ("#fd7e14", 3),  # Orange
        "info": ("#0d6efd", 2),  # Blue
        "information": ("#0d6efd", 2),  # Blue
        "success": ("#198754", 1),  # Green
        "connected": ("#198754", 1),  # Green
        "started": ("#198754", 1),  # Green
        "finished": ("#198754", 1),  # Green
        "debug": ("#6c757d", 0),  # Gray - lowest priority
    }

    # Keywords that should only highlight individual words, not entire lines
    WORD_ONLY_HIGHLIGHTS = {
        "timestamp": "#6c757d",  # Gray for timestamps
    }

    @staticmethod
    def highlight_text(text: str) -> str:
        """
        Highlight entire lines in log text with HTML colors based on severity keywords.

        Args:
            text (str): The raw log text to highlight

        Returns:
            str: HTML-formatted text with line-level highlighting
        """
        if not text.strip():
            return text

        lines = text.split("\n")
        highlighted_lines = []

        for line in lines:
            if not line.strip():
                highlighted_lines.append("")
                continue

            escaped_line = html.escape(line)

            highest_priority = -1
            chosen_color = None

            for keyword, (color, priority) in LogHighlighter.LINE_COLORS.items():
                if keyword.lower() in line.lower() and priority > highest_priority:
                    highest_priority = priority
                    chosen_color = color

            if chosen_color:
                formatted_line = (
                    f'<span style="color: {chosen_color}">{escaped_line}</span>'
                )
            else:
                formatted_line = escaped_line

            formatted_line = re.sub(
                r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?|\d{2}:\d{2}:\d{2})",
                r'<span style="color: #6c757d">\1</span>',
                formatted_line,
            )

            highlighted_lines.append(formatted_line)

        return "<br>".join(highlighted_lines)
