import json
import os
import sys

from java_object_utill.java_object_generator import ClassGenerator


def parse_all_files(core_path, start_package):
    for path, subdir, files in os.walk(core_path):
        for name in files:
            core_name, extension = os.path.splitext(name)
            if extension == ".json":
                parse_file(core_name, path, start_package + path.replace(core_path, "").replace('\\', '.'))


def parse_file(core_name, path, package):
    java_path = os.path.join(path, core_name + ".java")
    json_path = os.path.join(path, core_name + ".json")

    # Open the file and parse the JSON data
    f = open(json_path, )
    data = json.load(f)
    gen = ClassGenerator(data, core_name, package)

    # Parse the existing file if it exists for escape code
    if os.path.isfile(java_path):
        java_file = open(java_path, )
        java_file_lines = []
        with open(java_path, "r") as myFile:
            lines = java_file.readlines()
            lines = [line.rstrip() for line in lines]
        gen.process_existing_file(lines)


    # Generate the JavaObject
    file = gen.generate()

    # Write the file
    with open(java_path, "w") as myFile:
        lines = []
        file.write(lines)
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
