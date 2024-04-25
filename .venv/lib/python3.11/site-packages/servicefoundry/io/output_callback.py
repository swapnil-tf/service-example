class OutputCallBack:
    def print_header(self, line):
        print(line)

    def _print_separator(self):
        print("-" * 80)

    def print_line(self, line):
        print(line)

    def print_lines_in_panel(self, lines, header=None):
        self.print_header(header)
        self._print_separator()
        for line in lines:
            self.print_line(line)
        self._print_separator()

    def print_code_in_panel(self, lines, header=None, lang="python"):
        self.print_lines_in_panel(lines, header)

    def print(self, line):
        # just an alias
        self.print_line(line)
