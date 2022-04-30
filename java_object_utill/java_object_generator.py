import code_generator.java.java_code_generator
from code_generator.java.java_code_generator import *


class ClassGenerator:
    """
    A utility for generating a JavaObject class based on a json file

    Attributes:
        _json_data (dict):                  The file and class name
        class_name (str):                   The package string (x.x.x)
        _package (str):                     A list of import lines, should include blank lines for spacing as needed
        java_path (str):                    The path of the file
        field_prefix (str):                The main class of the file matching the name of the file
        _fields (list[dict]):               The fields to be writen
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
        self.field_prefix = self.class_name + "_Prefix"
        self._fields = self._json_data['fields']
        self._class_dict = class_dict
        self._follow_field = None
        self._full_fields = []

        self.file = JavaFile(class_name, package)

        # Populate optional parameters with defaults
        if 'abstract' not in self._json_data:
            self._json_data['abstract'] = False
        if 'implements' not in self._json_data:
            self._json_data['implements'] = None
        if 'listDef' not in self._json_data:
            self._json_data['listDef'] = False

        # For all fields, populate optional parameters with default
        for field in self._fields:
            field['key'] = class_name + "_" + field['name']
            if 'string_source' not in field:
                field['string_source'] = False
            if 'editable' not in field:
                field['editable'] = False
            if 'avoid_constructor' not in field:
                field['avoid_constructor'] = False
            if 'database_source' not in field:
                field['database_source'] = False
            if 'is_override' not in field:
                field['is_override'] = False
            if 'canBeNull' not in field:
                field['canBeNull'] = False
            if 'is_list' not in field:
                field['is_list'] = False
            if 'type' not in field:
                if 'listType' not in field:
                    raise Exception("Either type or listType must be declared in the JSON file")
                field['type'] = field['listType'] + "List"
                field['getType'] = "List<" + field['listType'] + ">"
            else:
                field['getType'] = field['type']
            if 'fieldType' not in field:
                field['fieldType'] = "DataField_Schema"

        if self._json_data['implements'] == "FileInterface":
            name_found = False
            path_found = False
            full_path_found = False
            for field in self._fields:
                if field['name'] == "FileName":
                    name_found = True
                    field['is_override'] = True
                if field['name'] == "ContainerPath":
                    path_found = True
                    field['is_override'] = True
                if field['name'] == "FullPath":
                    full_path_found = True
                    field['is_override'] = True
            if not name_found or not path_found or not full_path_found:
                raise Exception("FileInterface methods missing")

        # TODO remove
        for field in self._json_data['fields']:
            if 'dataCore' in field:
                field['avoid_constructor'] = True

    def get_full_field_list(self):
        """
        Get all the fields this class knows about, including its own and fields from its parents in the intended order

        Returns:
            A tuple consisting of the field that any children objects should follow and a list of all the fields this
            object knows about
        """
        if self._follow_field is None:
            self._follow_field, self._full_fields = self._class_dict[
                self._json_data['extends']].get_full_field_list()
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
        add_blank = False
        imports_start = False
        for line in file_lines:
            if line.startswith("import"):
                imports_start = True
                if add_blank:
                    self.file.append("")
                    add_blank = False
                self.file.append(line)
            elif line == "":
                if imports_start:
                    add_blank = True
            else:
                if imports_start:
                    break

    def generate(self):
        """
        Generate a JavaFile containing the JavaObject described in the JSON file

        Returns:
            The generated JavaFile ready to be writen
        """

        # Finalise self
        self.get_full_field_list()

        # Populate the header of the file
        self.file.javaClass.extensions = self._json_data['extends']
        self.file.javaClass.implements = self._json_data['implements']

        # Create the core class
        java_class = self.file.javaClass
        java_class.abstract = self._json_data['abstract']

        # Prepare each of the key sections
        keys = self._Keys(self)
        definitions = self._Definitions(self)
        properties = self._Properties(self)
        constructor = self._Constructor(self)
        implements = self._Implements(self)
        getters = self._Getters(self)
        setters = self._Setters(self)

        # Group all sections for convenience
        sections = [keys, definitions, properties, constructor, implements, getters, setters]
        for field in self._full_fields:
            if field in self._fields:
                for section in sections:
                    section.add_field(field)
            else:
                for section in sections:
                    section.add_virtual_field(field)

        # Add all code
        if self._json_data['listDef']:
            list_def_section = WritableSection()
            list_def_section.code_lines = False
            list_def_section.append(
                "public interface " + self.class_name + "List extends List<" + self.class_name + "> {")
            list_def_section.append("}")
            list_def_section.append("")
            java_class.append(list_def_section)
        keys.add(java_class)
        self._add_schema_method(java_class, definitions, properties)
        if not constructor.set_line.is_empty():
            self._add_min_constructor(java_class)
        if not self._json_data['abstract']:
            constructor.add(java_class)
        self._add_general_methods(java_class)
        implements.add(java_class)
        getters.add(java_class)
        setters.add(java_class)

        return self.file

    def _add_schema_method(self, java_class, definitions, properties):
        # Setup the method
        schema_method = code_generator.java.java_code_generator.JavaMethod("getDataObjectSchema")
        java_class.append(schema_method)
        schema_method.return_type = "DataObject_Schema"
        schema_method.static = True
        schema_method.comment.append("Get all the fields for this object")

        # Get the original schema to append
        schema_method.append(
            "DataObject_Schema dataObjectSchema = " + self._json_data['extends'] + ".getDataObjectSchema()")
        schema_method.append("")

        # Populate the definitions and properties as needed
        definitions.add(schema_method)
        properties.add(schema_method)

        # Close the method
        if self._json_data['abstract']:
            schema_method.append("return dataObjectSchema.endLayer(" + self.class_name + ".class)")
        else:
            schema_method.append("return dataObjectSchema.finaliseContainer(" + self.class_name + ".class)")

    def _add_min_constructor(self, java_class):
        constructor_method = JavaMethod(self.class_name)
        java_class.append(constructor_method)
        constructor_method.comment.append("Constructor")
        constructor_method.param.append("Database database")
        constructor_method.param.append("Object... args")
        constructor_method.append("super(database, args)")

    def _add_general_methods(self, java_class):
        section = WritableSection()

        if 'customToString' in self._json_data:
            to_string_method = JavaMethod("toString")
            to_string_method.return_type = "String"
            to_string_method.comment.append("@inheritDoc")
            to_string_method.attributes.append("@Override")
            to_string_method.append("return " + self._json_data['customToString'])
            section.append(to_string_method)
        else:
            for field in self._fields:
                if field['string_source']:
                    to_string_method = JavaMethod("toString")
                    to_string_method.return_type = "String"
                    to_string_method.comment.append("@inheritDoc")
                    to_string_method.attributes.append("@Override")
                    to_string_method.append("return get" + field['name'] + "()")
                    section.append(to_string_method)
                    break

        if not section.is_empty():
            java_class.append(SectionComment("General"))
            java_class.append(section)

    class _Keys:
        def __init__(self, parent):
            self._parent = parent
            self._section = WritableSection()
            self._prefix_needed = False

        def add_virtual_field(self, field):
            pass

        def add_field(self, field):
                self._prefix_needed = True
                self._section.append(
                    "public static final String " + field['key'] + " = " + self._parent.field_prefix + " + \"" + field[
                        'name'] + "\"")

        def add(self, java_class):
            if self._prefix_needed:
                java_class.append(
                    "private static final String " + self._parent.field_prefix + " = \"" +
                    self._parent.class_name + "_\"")
                java_class.append("")
            java_class.append(self._section)

    class _Definitions:
        def __init__(self, parent):
            self._parent = parent
            self._section = WritableSection()

        def add_virtual_field(self, field):
            self._section.append("// " + field['name'])
            pass

        def add_field(self, field):
            if field['canBeNull']:
                if field['is_list']:
                    self._section.append(
                        "dataObjectSchema.add(new ListDataField_Schema<>(" + field['key'] + ", " + field[
                            'type'] + "List.class, true))")
                else:
                    self._section.append(
                        "dataObjectSchema.add(new DataField_Schema<>(" + field['key'] + ", " + field[
                            'type'] + ".class, true))")
            else:
                if field['is_list']:
                    self._section.append(
                        "dataObjectSchema.add(new ListDataField_Schema<>(" + field['key'] + ", " + field[
                            'type'] + "List.class))")
                else:
                    self._section.append(
                        "dataObjectSchema.add(new DataField_Schema<>(" + field['key'] + ", " + field[
                            'type'] + ".class))")

        def add(self, method):
            self._section.append("")
            method.append(self._section)

    class _Properties:
        def __init__(self, parent):
            self._parent = parent
            self._section = WritableSection()

        def add_virtual_field(self, field):
            pass

        def add_field(self, field):
            any_used = False
            section = WritableSection()
            if 'properties' in field:
                any_used = True
                properties = field['attachedProperties']
                for key in properties:
                    for value in properties[key]:
                        section.append(
                            "dataObjectSchema.get(" + field['key'] + ").getProperty(" + key + ".class)." + value)
            if field['editable']:
                any_used = True
                section.append("dataObjectSchema.get(" + field['key'] + ").setManualCanEdit(true)")
            if 'dataCore' in field:
                any_used = True
                data_core = field['dataCore']
                if 'static' in data_core:
                    static = data_core['static']
                    section.append("dataObjectSchema.get(" + field[
                        'key'] + ").setDataCore_schema(new Static_DataCore_Schema<>(\"" + static['value'] + "\"))")
                elif 'derived' in data_core:
                    derived = data_core['derived']
                    data_core_section = WritableSection()
                    i = 0
                    data_core_section.code_lines = False
                    data_core_section.append(
                        "dataObjectSchema.<" + field['type'] + ">get(" + field['key'] + ").setDataCore_schema(")
                    data_core_section.append(
                        "        new Derived_DataCore_Schema<" + field['type'] + ", " + self._parent.class_name + ">")
                    data_core_section.append("                (container -> " + derived['codeLine'])
                    for source in derived['sources']:
                        line = "                        , " + source
                        i += 1
                        if i == len(derived['sources']):
                            line += "));"
                        data_core_section.append(line)

                    section.append(data_core_section)
                elif 'selfParent' in data_core:
                    self_parent = data_core['selfParent']
                    data_core_section = WritableSection()
                    data_core_section.code_lines = False

                    data_core_section.append(
                        "dataObjectSchema.<List<" + field['getType'] + ">>get(" + field[
                            'key'] + ").setDataCore_schema(")
                    data_core_section.append(
                        "        createSelfParentList(" + self_parent['classType'] + ".class, null));")
                    section.append(data_core_section)
                elif 'directDerived' in data_core:
                    direct_derived = data_core['directDerived']
                    data_core_section = WritableSection()
                    data_core_section.code_lines = False

                    data_core_section.append(
                        "dataObjectSchema.<" + field['getType'] + ">get(" + field['key'] + ").setDataCore_schema(")
                    if "defaultValue" in direct_derived:
                        data_core_section.append(
                            "        createDefaultDirectDerivedDataCore(" + str(direct_derived['defaultValue']) + ",")
                        data_core_section.append("                " + direct_derived['sources'] + "));")
                    elif "defaultGetter" in direct_derived:
                        data_core_section.append(
                            "        createDefaultDirectDerivedDataCoreGetter(" + str(
                                direct_derived['defaultGetter']) + ",")
                        data_core_section.append("                " + direct_derived['sources'] + "));")
                    else:
                        data_core_section.append(
                            "        createDirectDerivedDataCore(" + direct_derived['sources'] + "));")
                    section.append(data_core_section)
                elif 'multiParentList' in data_core:
                    multi_parent_list = data_core['multiParentList']
                    data_core_section = WritableSection()
                    data_core_section.code_lines = False

                    data_core_section.append(
                        "dataObjectSchema.<List<" + field['getType'] + ">>get(" + field[
                            'key'] + ").setDataCore_schema(")
                    # if "default" in data_core:
                    data_core_section.append(
                        "        createMultiParentList(" + field['getType'] + ".class, " + str(
                            multi_parent_list['parents']) + "));")
                    # else:
                    #     data_core_section.append("        createDirectDerivedDataCore(" + data_core['sources'] + "));")
                    section.append(data_core_section)
                else:
                    raise Exception("Unknown data core")

            if any_used:
                section.insert(0, DividerComment(field['name']))
                self._section.append(section)

        def add(self, method):
            if not self._section.is_empty():
                self._section.append(DividerComment())
                self._section.append("")
            method.append(self._section)

    class _Constructor:
        def __init__(self, parent):
            self._parent = parent
            self._method = JavaMethod(self._parent.class_name)
            self.set_line = WritableSection()
            self._database_source = None

        def add_virtual_field(self, field):
            self.add_field(field)

        def add_field(self, field):
            if not field['avoid_constructor']:
                # self._database_source['name'][0].lower() + self._database_source['name'][1:]

                self._method.param.append(field['type'] + " " + field['name'][0].lower() + field['name'][1:])
                self.set_line.append("        , " + field['key'] + ", " + field['name'][0].lower() + field['name'][1:])
                if field['database_source']:
                    self._database_source = field

        def add(self, java_class):
            # if self._set_line.is_empty():
            #     return

            # Setup the sections
            self.set_line.code_lines = False
            self._method.code_lines = False
            self._method.comment.append("Constructor")

            # Build the method
            if self._database_source is not None:
                self._method.append(
                    "super(" + self._database_source['name'][0].lower() + self._database_source['name'][1:] +
                    ".getTrackingDatabase()")
            else:
                self._method.param.insert(0, "Database database")
                self._method.append("super(database")
            # self._method.append("setAllValues(DataObject_Id, getTrackingDatabase().getNextId()")
            self._method.append(self.set_line)
            self._method.append(");")

            java_class.append(self._method)

    class _Implements:
        def __init__(self, parent):
            self._parent = parent
            self._methods = WritableSection()

        def add_virtual_field(self, field):
            pass

        def add_field(self, field):
            if field['is_override']:
                getter_method = JavaMethod("get" + field['name'])
                getter_method.comment.append("@inheritDoc")
                getter_method.attributes.append("@Override")
                getter_method.return_type = field['type']
                getter_method.append("return get(" + field['key'] + ")")
                self._methods.append(getter_method)

        def add(self, java_class):
            if not self._methods.is_empty():
                java_class.append(SectionComment("Implementations"))
                java_class.append(self._methods)

    class _Getters:
        def __init__(self, parent):
            self._parent = parent
            self._methods = WritableSection()

        def add_virtual_field(self, field):
            pass

        def add_field(self, field):
            if not field['is_override']:
                getter_method = JavaMethod("get" + field['name'])
                if field['is_list']:
                    getter_method.return_type = "List<" + field['getType'] + ">"
                else:
                    getter_method.return_type = field['getType']
                getter_method.append("return get(" + field['key'] + ")")
                self._methods.append(getter_method)

        def add(self, java_class):
            if not self._methods.is_empty():
                java_class.append(SectionComment("Getters"))
                java_class.append(self._methods)

    class _Setters:
        def __init__(self, parent):
            self._parent = parent
            self._methods = WritableSection()

        def add_virtual_field(self, field):
            pass

        def add_field(self, field):
            if field['editable']:
                setter_method = JavaMethod("set" + field['name'])
                setter_method.return_type = "void"
                setter_method.param.append(field['type'] + " " + field['name'][0].lower() + field['name'][1:])
                setter_method.append("set(" + field['key'] + ", " + field['name'][0].lower() + field['name'][1:] + ")")
                self._methods.append(setter_method)

        def add(self, java_class):
            if not self._methods.is_empty():
                java_class.append(SectionComment("Setters"))
                java_class.append(self._methods)


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
                             'avoid_constructor': True})
        self._fields.append({'name': "Children",
                             'type': "DataObjectList",
                             'avoid_constructor': True})

        self._follow_field = self._fields[0]
        self._full_fields = self._fields

    def set_class_dict(self, class_dict):
        pass

    def get_full_field_list(self):
        return self._follow_field, self._full_fields.copy()
