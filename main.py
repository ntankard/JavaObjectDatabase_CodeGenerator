import json
import os
import sys
import traceback

from java_object_utill.java_object_generator import ClassGenerator, RootClassGenerator


def parse_all_files(core_path, start_package):
    try:
        java_files = []
        java_files_dict = {'Displayable_DataObject': RootClassGenerator()}

        for path, subdir, files in os.walk(core_path):
            for name in files:
                core_name, extension = os.path.splitext(name)
                if extension == ".json":
                    file = parse_file(core_name, path, start_package + path.replace(core_path, "").replace('\\', '.'),
                                      java_files_dict)
                    java_files.append(file)
                    java_files_dict[file.class_name] = file

    except Exception as e:
        traceback.print_exc()
        print(e)
        return

    to_write = {}
    for java_file in java_files:
        try:
            to_write[java_file] = java_file.generate()
        except Exception as e:
            traceback.print_exc()
            print(e)
            return

    for java_file in java_files:
        write_file(java_file.java_path, to_write[java_file])


def parse_file(core_name, path, package, java_files_dict):
    java_path = os.path.join(path, core_name + ".java")
    json_path = os.path.join(path, core_name + ".json")

    # Open the file and parse the JSON data
    f = open(json_path, )
    data = json.load(f)
    gen = ClassGenerator(data, core_name, package, java_path, java_files_dict)

    # Parse the existing file if it exists for escape code
    if os.path.isfile(java_path):
        java_file = open(java_path, )
        with open(java_path, "r") as myFile:
            lines = java_file.readlines()
            lines = [line.rstrip() for line in lines]
        gen.process_existing_file(lines)

    # Generate the JavaObject
    return gen


def write_file(java_path, file):
    # Write the file
    with open(java_path, "w") as myFile:
        lines = []
        file.write(lines, 0)
        for line in lines:
            myFile.write(line)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    _start_package = ""
    _core_path = ""
    if len(sys.argv) == 3:
        _start_package = sys.argv[1]
        _core_path = sys.argv[2]
    else:
        print("Both a path to the folder to parse and a core path must be provided")
        exit(2)

    parse_all_files(_core_path, _start_package)
