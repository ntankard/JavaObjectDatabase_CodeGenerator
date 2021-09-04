import code_generator.java.java_code_generator


class ClassGenerator:
    """
    A utility for generating a JavaObject class based on a json file

    Attributes:
        _json_data (dict):      The file and class name
        _class_name (str):      The package string (x.x.x)
        _package (str):         A list of import lines, should include blank lines for spacing as needed
        _field_prefix (str):    The main class of the file matching the name of the file
        _fields (dict):         The fields to be writen
        _imports(list[str]):    The imports to add at the top of the file
    """

    def __init__(self, json, class_name, package):
        """
        A utility for generating a JavaObject class based on a json file

        Args:
            json (dict):        The raw json data describing the class to be generated
            class_name (str):   The name of the class
            package (str):      The package the class lives in
        """
        self._json_data = json
        self._class_name = class_name
        self._package = package
        self._field_prefix = self._class_name + "_Prefix"
        self._fields = self._json_data['fields']
        self._imports = []

        for field in self._json_data['fields']:
            field['key'] = class_name + "_" + field['name']

    def process_existing_file(self, file_lines):
        for line in file_lines:
            if line.startswith("import"):
                self._imports.append(line)

    def generate(self):
        """
        Generate a JavaFile containing the JavaObject described in the JSON file

        Returns:
            The generated JavaFile ready to be writen
        """
        file = code_generator.java.java_code_generator.JavaFile(self._class_name, self._package)

        # Populate the header of the file
        file.get_core_class().extensions.append(self._json_data['extends'])
        for line in self._imports:
            file.imports.append(line)

        # Create the core class
        java_class = file.get_core_class()
        self._add_field_key_definitions(java_class)
        self._add_schema_method(java_class)
        self._add_min_constructor(java_class)
        self._add_full_constructor(java_class)
        self._add_getters(java_class)

        return file

    def _add_field_key_definitions(self, java_class):
        # Add the prefix
        java_class.lines.append("")
        java_class.lines.append(
            "private static final String " + self._field_prefix + " = \"" + self._class_name + "_\"")
        java_class.lines.append("")

        # All all the fields
        for field in self._fields:
            java_class.lines.append("public static final String " + field['key'] +
                                    " = " + self._field_prefix + " + \"" + field['name'] + "\"")

    def _add_schema_method(self, java_class):
        # Setup the method
        schema_method = java_class.add_method("getDataObjectSchema")
        schema_method.return_type = "DataObject_Schema"
        schema_method.static = True
        schema_method.comment.append("Get all the fields for this object")

        # Get the original schema to append
        schema_method.lines.append(
            "DataObject_Schema dataObjectSchema = " + self._json_data['extendsSchema'] + ".getDataObjectSchema()")
        schema_method.lines.append("")

        # Add all the new fields
        for field in self._fields:
            schema_method.lines.append(
                "dataObjectSchema.add(new DataField_Schema<>(" + field['key'] + ", " + field['type'] + ".class))")
        schema_method.lines.append("")

        # Close the method
        schema_method.lines.append("return dataObjectSchema.finaliseContainer(" + self._class_name + ".class)")

    def _add_min_constructor(self, java_class):
        constructor_method = java_class.add_method(self._class_name)
        constructor_method.comment.append("Constructor")
        constructor_method.param.append("Database database")
        constructor_method.lines.append("super(database)")

    def _add_full_constructor(self, java_class):
        # Setup the method
        full_constructor_method = java_class.add_method(self._class_name)
        full_constructor_method.comment.append("Constructor")
        database_source = None

        # Setup the set call and parameters
        set_line = "setAllValues(DataObject_Id, getTrackingDatabase().getNextId()\n"
        for field in self._fields:
            full_constructor_method.param.append(field['type'] + " " + field['name'].lower())
            set_line += "                , " + field['key'] + ", " + field['name'].lower() + '\n'
            if 'database_source' in field and field['database_source']:
                database_source = field
        set_line += "       )"
        full_constructor_method.lines.append(set_line)

        # Add the database source
        if database_source is not None:
            full_constructor_method.lines.insert(0, "this(" + database_source['name'].lower() +
                                                 ".getTrackingDatabase())")
        else:
            full_constructor_method.param.insert(0, "Database database")
            full_constructor_method.lines.insert(0, "this(database)")

    def _add_getters(self, java_class):
        java_class.add_method_divider("Getters")
        for field in self._fields:
            getter_method = java_class.add_method("get" + field['name'])
            getter_method.return_type = field['type']
            getter_method.lines.append("return get(" + field['key'] + ")")
