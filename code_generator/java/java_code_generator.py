class JavaFile:
    """
    The top level container for an a java file to write.

    Attributes:
        _name (str):            The file and class name
        _package (str):         The package string (x.x.x)
        imports (list[str]):    A list of import lines, should include blank lines for spacing as needed
        _javaClass (JavaClass): The main class of the file matching the name of the file
    """

    def __init__(self, name, package):
        """
        Constructor

        Args:
            name (str):       The file and class name
            package (str):    The package string (x.x.x)
        """

        self._name = name
        self._package = package
        self.imports = []
        self._javaClass = JavaClass(name, 0)

    def write(self, file_lines):
        """
        Add the generated lines of this file to an output list to write to a file

        Args:
            file_lines (list[str]): OUT The lines to write
        """

        # Add the package
        add_code_line("package " + self._package, file_lines, 0)
        blank_line(file_lines)

        # Add the imports
        if len(self.imports) != 0:
            for line in self.imports:
                add_line(line, file_lines, 0)
            blank_line(file_lines)

        self._javaClass.write(file_lines)

    def get_core_class(self):
        return self._javaClass


class JavaClass:
    """
    A class to add to the file (top level or inner class TODO)

    Attributes:
        _name (str):                                The name of the class
        abstract (bool):                            True if the class is abstract
        extensions (list[str]):                     The classes this class extends
        lines (list[str]):                          Any lines to be written at the start of a class outside the scope
                                                    of a method (parameters, consts ect)
        _methods (list[JavaMethod/MethodDivider]):  All the methods to be written to the class in order
        _tab_offset (int):                          The number of tabs that the class should be offset by
    """

    def __init__(self, name, tab_offset):
        """
        Constructor

        Args:
            name (str):         The name of the class
            tab_offset (int):   The number of tabs that the class should be offset by
        """
        self._name = name
        self.abstract = False
        self.extensions = []
        self.lines = []
        self._methods = []
        self._tab_offset = tab_offset

    def add_method(self, name):
        """
        Create and add a new method to the class

        Args:
            name (str): The name of the method

        Returns:
            The newly created JavaMethod
        """
        method = JavaMethod(name, self._tab_offset + 1)
        self._methods.append(method)
        return method

    def add_method_divider(self, name):
        """
        Create and add a new method divider to the class

        Args:
            name (str): The name of the divider
        """
        self._methods.append(MethodDivider(name, self._tab_offset + 1))

    def write(self, file_lines):
        """
        Add the generated lines of this class to an output list to write to a file

        Args:
            file_lines (list[str]): OUT The lines to write
        """

        self._add_class_definition(file_lines)
        self._add_non_method_lines(file_lines)
        self._add_methods(file_lines)

        # End class
        add_line("}", file_lines, self._tab_offset)

    def _add_class_definition(self, file_lines):
        class_line = "public "
        if self.abstract:
            class_line += "abstract "
        class_line += "class " + self._name
        if len(self.extensions) != 0:
            class_line += " extends "
            for extension in self.extensions:
                class_line += extension
        class_line += " {"
        add_line(class_line, file_lines, self._tab_offset)

    def _add_non_method_lines(self, file_lines):
        for line in self.lines:
            if len(line) == 0:
                file_lines.append('\n')
            else:
                add_code_line(line, file_lines, self._tab_offset + 1)

    def _add_methods(self, file_lines):
        for method in self._methods:
            file_lines.append('\n')
            method.write(file_lines)


class MethodDivider:
    """
    A comment section used to divide groups of methods to write to the file

    Attributes:
        _name (str):            The name of the method
        _tab_offset (int):      The number of tabs that the method should be offset by
    """

    def __init__(self, name, tab_offset):
        """
        Constructor

        Args:
            name (str):         The name of the divider
            tab_offset (int):   The number of tabs that the method should be offset by
        """
        self._name = name
        self._tab_offset = tab_offset

    def write(self, file_lines):
        """
        Add the generated lines of this divider to an output list to write to a file

        Args:
            file_lines (list[str]): OUT The lines to write
        """
        # Method comment
        line_size = 118 - (4 * self._tab_offset)
        pad_size = int((line_size - (len(self._name) + 2)) / 2)

        line = "//"
        for x in range(line_size):
            line += "-"

        center_line = "//"
        for x in range(pad_size):
            center_line += "#"
        center_line += (" " + self._name + " ")
        for x in range(pad_size):
            center_line += "#"
        if ((pad_size * 2) + 2 + len(self._name)) != line_size:
            center_line += "#"

        add_line(line, file_lines, self._tab_offset)
        add_line(center_line, file_lines, self._tab_offset)
        add_line(line, file_lines, self._tab_offset)


class JavaMethod:
    """
    A method inside a class to write to the file

    Attributes:
        _name (str):            The name of the method
        static (bool):          True if the method should be declared static?
        public (bool):          True if the method should be declared public (otherwise private) (TODO protected)
        comment (list[str]):    A list of lines to add to the comment ahead of the method
        attributes (list[str]): Any attributes to be tagged on the method
        param (list[str]):      A list of parameters to add to the method signature (type and name e.g. "Foo foo")
        return_type (str):      The return type of the method
        lines (list[str]):      The lines of code in the body of the method including gaps as needed
        _tab_offset (int):      The number of tabs that the method should be offset by
    """

    def __init__(self, name, tab_offset):
        """
        Constructor

        Args:
            name (str):         The name of the method
            tab_offset (int):   The number of tabs that the method should be offset by
        """
        self._name = name
        self.static = False
        self.public = True
        self.comment = []
        self.attributes = []
        self.param = []
        self.return_type = None
        self.lines = []
        self._tab_offset = tab_offset

    def write(self, file_lines):
        """
        Add the generated lines of this method to an output list to write to a file

        Args:
            file_lines (list[str]): OUT The lines to write
        """
        # Method comment
        self._add_method_comment(file_lines)
        if len(self.attributes) != 0:
            self._add_attributes(file_lines)
        self._add_method_signature(file_lines)
        self._add_lines(file_lines)

        # End of method
        add_line("}", file_lines, self._tab_offset)

    def _add_method_comment(self, file_lines):
        if len(self.comment) != 0:
            add_line("/**", file_lines, self._tab_offset)
            for line in self.comment:
                add_line(" * " + line, file_lines, self._tab_offset)
            add_line(" */", file_lines, self._tab_offset)

    def _add_attributes(self, file_lines):
        atr_line = ""
        for line in self.attributes:
            atr_line += line
        add_line(atr_line, file_lines, self._tab_offset)

    def _add_method_signature(self, file_lines):
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
        add_line(method_line, file_lines, self._tab_offset)

    def _add_lines(self, file_lines):
        for line in self.lines:
            if len(line) == 0:
                file_lines.append('\n')
            else:
                add_code_line(line, file_lines, self._tab_offset + 1)



def add_code_line(text, file_lines, tabs):
    """
    Add a line of code, with tabs in front of it and a ; with a end of line at the end

    Args:
        text(str):              The line of text to write
        file_lines (list[str]): OUT The lines to write
        tabs (int):             The number of tabs to write
    """
    line = ""
    for x in range(tabs):
        line += "    "
    line += text
    if text.endswith("{") or text.endswith("}"):
        line += "\n"
    else:
        line += ";\n"
    file_lines.append(line)


def blank_line(file_lines):
    """
    Add a blank line
    Args:
        file_lines (list[str]): OUT The lines to write
    """
    add_line("", file_lines, 0)


def add_line(text, file_lines, tabs):
    """
    Add a line of code, with tabs in front of it and a end of line at the end

    Args:
        text(str):              The line of text to write
        file_lines (list[str]): OUT The lines to write
        tabs (int):             The number of tabs to write
    """
    line = ""
    for x in range(tabs):
        line += "    "
    line += text
    line += '\n'
    file_lines.append(line)
