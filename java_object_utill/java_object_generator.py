import code_generator.java.java_code_generator


class ClassGenerator:
    """
    A utility for generating a JavaObject class based on a json file

    Attributes:
        _json_data (dict):                  The file and class name
        class_name (str):                   The package string (x.x.x)
        _package (str):                     A list of import lines, should include blank lines for spacing as needed
        java_path (str):                    The path of the file
        _field_prefix (str):                The main class of the file matching the name of the file
        _fields (list[dict]):               The fields to be writen
        _imports (list[str]):               The imports to add at the top of the file
        _abstract (bool):                   True if the class is abstract
        _has_general (bool)                 Does this class have any additional general methods
        _has_setter (bool)                  Do any of the fields require setters
        _class_dict (dict{ClassGenerator}): A dict containing all ClassGenerator found in the package mapped to there
                                            class name
        _follow_field (dict)                The field that any new fields should follow to maintain the intended order
        _full_fields (list(dict))           All fields in order that this class can use, including its own and parents
    """

    def __init__(self, json, class_name, package, java_path, class_dict):
        """
        A utility for generating a JavaObject class based on a json file

        Args:
            json (dict):        The raw json data describing the class to be generated
            class_name (str):   The name of the class
            package (str):      The package the class lives in
            java_path (str):    The path of the file
        """
        self._json_data = json
        self.class_name = class_name
        self._package = package
        self.java_path = java_path
        self._field_prefix = self.class_name + "_Prefix"
        self._fields = self._json_data['fields']
        self._imports = []
        self._abstract = 'abstract' in self._json_data and self._json_data['abstract']
        self._has_general = False
        self._has_setter = False
        self._class_dict = class_dict
        self._follow_field = None
        self._full_fields = []

        for field in self._json_data['fields']:
            field['key'] = class_name + "_" + field['name']
            if 'string_source' in field and field['string_source']:
                self._has_general = True
            if 'editable' in field and field['editable']:
                self._has_setter = True

    def get_full_field_list(self):
        """
        Get all the fields this class knows about, including its own and fields from its parents in the intended order

        Returns:
            A tuple consisting of the field that any children objects should follow and a list of all the fields this
            object knows about
        """
        if self._follow_field is None:
            self._follow_field, self._full_fields = self._class_dict[
                self._json_data['extendsSchema']].get_full_field_list()
            for field in self._fields:
                self._full_fields.insert(self._full_fields.index(self._follow_field) + 1, field)
                self._follow_field = field

        return self._follow_field, self._full_fields.copy()

    def process_existing_file(self, file_lines):
        """
        Read the existing generated file to extract any needed data

        Args:
            file_lines (list[str]): The lines of the previously generated file
        """
        for line in file_lines:
            if line.startswith("import"):
                self._imports.append(line)

    def generate(self):
        """
        Generate a JavaFile containing the JavaObject described in the JSON file

        Returns:
            The generated JavaFile ready to be writen
        """

        # Finalise self
        self.get_full_field_list()
        file = code_generator.java.java_code_generator.JavaFile(self.class_name, self._package)

        # Populate the header of the file
        file.get_core_class().extensions.append(self._json_data['extends'])
        for line in self._imports:
            file.imports.append(line)

        # Create the core class
        java_class = file.get_core_class()
        java_class.abstract = self._abstract

        # Add all code
        self._add_field_key_definitions(java_class)
        self._add_schema_method(java_class)
        self._add_min_constructor(java_class)
        if not self._abstract:
            self._add_full_constructor(java_class)
        if self._has_general:
            self._add_general_methods(java_class)
        self._add_getters(java_class)
        if self._has_setter:
            self._add_setters(java_class)

        return file

    def _add_field_key_definitions(self, java_class):
        # Add the prefix
        java_class.lines.append("")
        java_class.lines.append(
            "private static final String " + self._field_prefix + " = \"" + self.class_name + "_\"")
        java_class.lines.append("")

        # All all the fields
        for field in self._fields:
            if 'use_get_name' in field and field['use_get_name']:
                java_class.lines.append("public static final String " + field['key'] +
                                        " = \"get" + field['name'] + "\"")
            else:
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
        for field in self._full_fields:
            if field in self._fields:
                # for field in self._fields:
                schema_method.lines.append(
                    "dataObjectSchema.add(new DataField_Schema<>(" + field['key'] + ", " + field['type'] + ".class))")
            else:
                schema_method.lines.append("// " + field['name'])
        schema_method.lines.append("")

        self._add_field_config(schema_method)

        # Close the method
        if self._abstract:
            schema_method.lines.append("return dataObjectSchema.endLayer(" + self.class_name + ".class)")
        else:
            schema_method.lines.append("return dataObjectSchema.finaliseContainer(" + self.class_name + ".class)")

    def _add_field_config(self, schema_method):
        any_print = False
        for field in self._fields:
            if 'editable' in field and field['editable']:
                any_print = True
                divide_line = "// " + field['name'] + " "
                for x in range(108 - len(field['name'])):
                    divide_line += "="
                schema_method.lines.append(divide_line)
                schema_method.lines.append("dataObjectSchema.get(" + field['key'] + ").setManualCanEdit(true)")
        if any_print:
            divide_line = "//"
            for x in range(110):
                divide_line += "="
            schema_method.lines.append(divide_line)
            schema_method.lines.append("")

    def _add_min_constructor(self, java_class):
        constructor_method = java_class.add_method(self.class_name)
        constructor_method.comment.append("Constructor")
        constructor_method.param.append("Database database")
        constructor_method.lines.append("super(database)")

    def _add_full_constructor(self, java_class):
        # Setup the method
        full_constructor_method = java_class.add_method(self.class_name)
        full_constructor_method.comment.append("Constructor")
        database_source = None

        # Setup the set call and parameters
        set_line = "setAllValues(DataObject_Id, getTrackingDatabase().getNextId()\n"
        for field in self._full_fields:
            if not ('avoid_constructor' in field) or (not field['avoid_constructor']):
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

    def _add_general_methods(self, java_class):
        java_class.add_method_divider("General")
        for field in self._fields:
            if 'string_source' in field and field['string_source']:
                to_string_method = java_class.add_method("toString")
                to_string_method.return_type = "String"
                to_string_method.comment.append("@inheritDoc")
                to_string_method.attributes.append("@Override")

                to_string_method.lines.append("return get" + field['name'] + "()")
                break

    def _add_getters(self, java_class):
        java_class.add_method_divider("Getters")
        for field in self._fields:
            getter_method = java_class.add_method("get" + field['name'])
            getter_method.return_type = field['type']
            getter_method.lines.append("return get(" + field['key'] + ")")

    def _add_setters(self, java_class):
        java_class.add_method_divider("Setters")
        for field in self._fields:
            if 'editable' in field and field['editable']:
                setter_method = java_class.add_method("set" + field['name'])
                setter_method.return_type = "void"
                setter_method.param.append(field['type'] + " " + field['name'].lower())
                setter_method.lines.append("set(" + field['key'] + ", " + field['name'].lower() + ")")


class RootClassGenerator:
    """
    A thin, dummy ClassGenerator used to be the root of all get_full_field_list calls. This class is needed as all
    DataObject's inherit from a central class that is not defined in the same package as all the objects. See
    ClassGenerator for documentation
    """

    def __init__(self):
        self._class_name = "Displayable_DataObject"
        self._fields = []
        self._fields.append({'name': "ID",
                             'type': "Integer",
                             'use_get_name': True,
                             'avoid_constructor': True})
        self._fields.append({'name': "Children",
                             'type': "DataObjectList",
                             'use_get_name': True,
                             'avoid_constructor': True})

        self._follow_field = self._fields[0]
        self._full_fields = self._fields

    def set_class_dict(self, class_dict):
        pass

    def get_full_field_list(self):
        return self._follow_field, self._full_fields.copy()
