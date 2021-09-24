class WritableSection:
    """
    A shared interface to allow interchangeable blocks of code to be written to a file

    Attributes:
        _file_lines (list[str]):                The lines that will be written to file (set at write time)
        _tab_offset (int):                      The number of tabs that the class should be offset by, set at write time
        _sections (list[str/WritableSection]):  The lines or other sections to write
        _code_lines (bool):                     Are the lines code (with a ;) or not (does not effect nested sections)
    """

    def __init__(self):
        """
        Constructor
        """
        self._file_lines = []
        self._tab_offset = 0
        self._sections = []
        self._code_lines = True

    def append(self, section):
        """
        Add a section

        Args:
            section (str/WritableSection):       The line or WritableSection to add
        """
        self._sections.append(section)

    def insert(self, index, section):
        """
        Insert a section at a specific index

        Args:
            index (int):                    The index to add to
            section (str/WritableSection):  The line or WritableSection to add
        """
        self._sections.insert(index, section)

    def is_empty(self):
        """
        Check if the core sections to write are empty. Some data can still be written even if this is empty depending
        on implementation (an empty method for example)

        Returns:
            True if the core sections to write are empty
        """
        return len(self._sections) == 0

    def write(self, file_lines, tab_offset):
        """
        Add the sections and/or lines to an output list to write to a file

        Args:
            file_lines (list[str]): OUT The lines to write
            tab_offset (int):       The number of tabs that the class should be offset by
        """
        self._file_lines = file_lines
        self._tab_offset = tab_offset
        self._write_section()

    def _write_section(self, tab_delta=0):
        old_tab = self._tab_offset
        self._tab_offset += tab_delta
        for line in self._sections:
            if issubclass(type(line), WritableSection):
                line.write(self._file_lines, self._tab_offset)
            else:
                if self._code_lines:
                    self._add_code_line(line)
                else:
                    self._add_line(line)
        self._tab_offset = old_tab

    def _blank_line(self):
        """
        Add a blank line
        """
        self._file_lines.append('\n')

    def _add_code_line(self, text, tabs=0):
        """
        Add a line of code, with tabs in front of it and a ; with a end of line at the end

        Args:
            text(str):              The line of text to write
            tabs (int):             The number of tabs to write above the base tab offset of this section
        """
        line = ""
        if len(text) != 0:
            for x in range(self._tab_offset + tabs):
                line += "    "
            line += text
            if text.endswith("{") or text.endswith("}") or text.startswith("//") or text.endswith(";") or len(
                    text) == 0:
                line += "\n"
            else:
                line += ";\n"
            self._file_lines.append(line)
        else:
            self._blank_line()

    def _add_line(self, text, tabs=0):
        """
        Add a line of code, with tabs in front of it and a end of line at the end

        Args:
            text(str):              The line of text to write
            tabs (int):             The number of tabs to write above the base tab offset of this section
        """
        line = ""
        if len(text) != 0:
            for x in range(self._tab_offset + tabs):
                line += "    "
            line += text
            line += '\n'
            self._file_lines.append(line)
        else:
            self._blank_line()


class JavaFile(WritableSection):
    """
    The top level container for an a java file to write.

    Attributes:
        _name (str):            The file and class name
        _package (str):         The package string (x.x.x)
        javaClass (JavaClass): The main class of the file matching the name of the file
    """

    def __init__(self, name, package):
        """
        Constructor

        Args:
            name (str):       The file and class name
            package (str):    The package string (x.x.x)
        """

        super().__init__()
        self._name = name
        self._package = package
        self.javaClass = JavaClass(name)

    def write(self, file_lines, tab_offset):
        self._file_lines = file_lines
        self._tab_offset = tab_offset

        # Add the package
        self._add_code_line("package " + self._package)

        # Add the imports
        if not self.is_empty():
            self._blank_line()
        super()._write_section()

        # Add the class
        self.javaClass.write(file_lines, tab_offset)


class JavaClass(WritableSection):
    """
    A class to add to the file (top level or inner class TODO)

    Attributes:
        _name (str):                            The name of the class
        abstract (bool):                        True if the class is abstract
        extensions (list[str]):                 The classes this class extends
    """

    def __init__(self, name):
        """
        Constructor

        Args:
            name (str):         The name of the class
        """
        super().__init__()
        self._name = name
        self.abstract = False
        self.extensions = []

    def write(self, file_lines, tab_offset):
        self._file_lines = file_lines
        self._tab_offset = tab_offset

        self._blank_line()
        self._add_class_definition()
        self._blank_line()
        super()._write_section(1)
        self._add_line("}")

    def _add_class_definition(self):
        class_line = "public "
        if self.abstract:
            class_line += "abstract "
        class_line += "class " + self._name
        if len(self.extensions) != 0:
            class_line += " extends "
            for extension in self.extensions:
                class_line += extension
        class_line += " {"
        self._add_line(class_line)


class SectionComment(WritableSection):
    """
    A comment section used to divide groups of methods to write to the file

    Attributes:
        _comment (str): The comment to write
    """

    def __init__(self, comment):
        """
        Constructor

        Args:
            comment (str):         The name of the divider
        """
        super().__init__()
        self._comment = comment

    def write(self, file_lines, tab_offset):
        self._file_lines = file_lines
        self._tab_offset = tab_offset

        # Separate
        self._blank_line()

        # Method comment
        line_size = 118 - (4 * self._tab_offset)
        pad_size = int((line_size - (len(self._comment) + 2)) / 2)

        line = "//"
        for x in range(line_size):
            line += "-"

        center_line = "//"
        for x in range(pad_size):
            center_line += "#"
        center_line += (" " + self._comment + " ")
        for x in range(pad_size):
            center_line += "#"
        if ((pad_size * 2) + 2 + len(self._comment)) != line_size:
            center_line += "#"

        self._add_line(line)
        self._add_line(center_line)
        self._add_line(line)


class BlockComment(WritableSection):
    """
    A comment section used to divide groups of methods to write to the file

    Attributes:
        _lines (list[str]): The lines of the comment block
    """

    def __init__(self):
        super().__init__()
        self._lines = []

    def append(self, section):
        """
        Add a comment lines

        Args:
            section (str): The line  to add
        """
        # TODO check for type
        self._lines.append(section)

    def write(self, file_lines, tab_offset):
        self._file_lines = file_lines
        self._tab_offset = tab_offset

        if len(self._lines) != 0:
            self._add_line("/**")
            for line in self._lines:
                self._add_line(" * " + line)
            self._add_line(" */")


class JavaMethod(WritableSection):
    """
    A method inside a class to write to the file

    Attributes:
        _name (str):                            The name of the method
        static (bool):                          True if the method should be declared static?
        public (bool):                          True if the method should be declared public (otherwise private) (TODO protected)
        comment (list[str]):                    A list of lines to add to the comment ahead of the method
        attributes (list[str]):                 Any attributes to be tagged on the method
        param (list[str]):                      A list of parameters to add to the method signature (type and name e.g. "Foo foo")
        return_type (str):                      The return type of the method
    """

    def __init__(self, name):
        """
        Constructor

        Args:
            name (str):         The name of the method
        """
        super().__init__()
        self._name = name
        self.static = False
        self.public = True
        self.comment = BlockComment()
        self.attributes = []
        self.param = []
        self.return_type = None

    def write(self, file_lines, tab_offset):
        self._file_lines = file_lines
        self._tab_offset = tab_offset

        self._blank_line()
        self.comment.write(self._file_lines, self._tab_offset)
        self._add_attributes()
        self._add_method_signature()
        super()._write_section(1)
        self._add_line("}")

    def _add_attributes(self):
        if len(self.attributes) != 0:
            atr_line = ""
            for line in self.attributes:
                atr_line += line
            self._add_line(atr_line)

    def _add_method_signature(self):
        method_line = ""
        if self.public:
            method_line += "public "
        else:
            method_line += "private "
        if self.static:
            method_line += "static "
        if self.return_type is not None:
            method_line += self.return_type + " "
        method_line += self._name + "("
        i = 0
        for param in self.param:
            method_line += param
            if (i + 1) != len(self.param):
                method_line += ", "
            i += 1
        method_line += ") {"
        self._add_line(method_line)
