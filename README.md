# cocodeChecker

Check the commented-out code in cpp source files.

## Overview


In order to detect redundant code components in C++ source file comments, this project was created.
The output file can be integrated into the output xml of cppcheck, which can be used for sonarqube's custom rule detection. 


## Dependencies

[Python3](https://www.python.org/)

[llvm-project](https://github.com/llvm/llvm-project/tree/main/clang/bindings/python)

## Install

```
pip install libclang lxml
```

```
git clone https://github.com/Nishikinor/cocodeChecker.git
```

## Usage

Download llvm, then set the local libclang path in environment variable.
```
# Windows
set CLANG_LIBRARY_PATH="C:\path\to\your\libclang.dll"

# Linux
export CLANG_LIBRARY_PATH="/path/to/your/libclang.so"
```

Then you can use it from the command line.
```
python cocode.py -h
usage: Remove the comment-out cpp code [-h] [--dir [DIR]] [--file FILE] [--dump_xml DUMP_XML] [--add_xml ADD_XML] [--remove_cocode REMOVE_COCODE]

optional arguments:
  -h, --help            show this help message and exit
  --dir [DIR]           Name of directory to process.
  --file FILE           A single file to process.
  --dump_xml DUMP_XML   Dump the result into a xml file according to the format of cppcheck.
  --add_xml ADD_XML     Add the scan result into the exists xml file.
  --remove_cocode REMOVE_COCODE
                        Remove the comment-out cpp code in source file.
```

## Examples

Scan the whole source directory and output the result to a xml: 
```
python cocode.py --dir examples/ --dump_xml output.xml
```

Append new xml elements in a exists xml file from scan result:
```
python cocode.py --dir MyProject/ --add_xml MyProject/cppcheck.xml
```

## License

MIT