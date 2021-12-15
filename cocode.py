import pathlib
import clang.cindex
import argparse
import xml.etree.ElementTree as ET
import sys
import re
import platform
from xml.dom import minidom
from collections import defaultdict


#TODO: Now this module can only process the current working directory.
#      The next step is to support the use of arbitrary paths
CocodeContainer = defaultdict(list) # k-v type: {filename: list[tuple(line, column)]}

def getfiles_fromdir(dirname: str, extensions={'.cpp', '.hpp', '.cc', '.h', 'cxx', 'c'}):
    '''Get cpp source files from directory
    Returns: list[Pathobj]
    '''
    p = pathlib.Path(dirname)
    filelist = []
    for path in p.glob(r'**/*'):
        if path.suffix in extensions:
            filelist.append(path)
    
    return filelist   

    
def remove_comments(filepath, comment_list):
    '''Remove the specfied comments in filepath
    param filepath: String
    param comment_list: list[Pathobj]
    TODO: refactor this method.
    '''
    with open(filepath, 'r') as filehandle:
        file_content = filehandle.read()
    
    with open(filepath, 'w') as wfilehandle:
        for comment_text in comment_list:
            if "\r\n" in comment_text:
                comment_text = comment_text.replace('\r\n', '\n')
            file_content = file_content.replace(comment_text, '')
            
        wfilehandle.write(file_content)

def getlineandcolumn(loc: clang.cindex.SourceLocation):
    return loc.line, loc.column

def generate_childnodes(root, container):
    
    err_attr = {
        "id": "CommentedoutCode",
        "severity": "style",
        "msg": "Section of code should not be commented out.",
        "verbose": "Section of code should not be commented out."
    }

    for filepath, tuplelist in container.items():
        for position in tuplelist:
            line = position[0]
            column = position[1]
            loc_attr = {
                "file": str(filepath),
                'line': str(line),
                'column': str(column),
            }
            for errors in root.iter("errors"):
                new_error = ET.SubElement(errors, "error", err_attr)
                ET.SubElement(new_error, "location", loc_attr)
                
def writefmtxml(xmlname: str, tree: ET, root: ET.Element):
    # Save the formatted xml document by indentation spaces.
    if sys.version_info.major == 3 and sys.version_info.minor >= 9:
        ET.indent(tree)
        tree.write(xmlname)
    else:
        pretty_xml = minidom.parseString(ET.tostring(root)).toprettyxml(indent="    ")
        with open(xmlname, "w") as f:
            f.write(pretty_xml)

def dumpxml(xmlname: str, container: CocodeContainer):
    '''TODO:Dump the xml file according to the format of cppcheck
    '''
    xmlfile = pathlib.Path(xmlname)
    
    if xmlfile.exists():
        raise OSError(f"The {xmlname} file already exists.")
    
    tree = ET.ElementTree("results")
    ET.SubElement(tree, "errors")
    root = tree.getroot()

    generate_childnodes(root, container)
    writefmtxml(xmlname, tree, root)
    
    
    
def addtoxml(xmlname: str, container: CocodeContainer):
    '''Add the content to a exists xml file according to the format of cppcheck
    '''
    xmlfile = pathlib.Path(xmlname)
    
    if not xmlfile.exists():
        raise FileNotFoundError(f"Can't find the xml file: {xmlname}")
    
    tree = ET.parse(xmlname)
    root = tree.getroot()
    
    generate_childnodes(root, container)
    writefmtxml(xmlname, tree, root)
        

def cppparser(filepath: str) -> CocodeContainer:
    '''Parse the comment section of a cpp source file.
    '''
    idx = clang.cindex.Index.create()
    raw_tu = idx.parse(filepath, args=['-std=c++11'])
    raw_tu_tokens = raw_tu.get_tokens(extent=raw_tu.cursor.extent)
    comment_list = []
    cocode_container = defaultdict(list)
    
    for r_t in raw_tu_tokens:
        if r_t.kind.name != "COMMENT":
            continue
        
        try:
            comment_content = r_t.spelling
        except UnicodeDecodeError:
            continue
        
        match = re.match(r"[^\x00-\x7f]", comment_content, flags=re.UNICODE | re.IGNORECASE)
        if match:
            continue
        
        if comment_content.startswith('//') and ("copyright" not in comment_content.lower()):
            comment_content = comment_content.lstrip('//')
        
        if comment_content.startswith("/*") and ("copyright" not in comment_content.lower()):
            comment_content = comment_content.lstrip("/*")
            comment_content = comment_content.rstrip("*/")
            
        idx_comment = clang.cindex.Index.create()
        tu = idx_comment.parse('tmp.cpp',
                               args=['-std=c++11'], 
                               unsaved_files=[('tmp.cpp', comment_content)],
                               options=0
        )
        
        isEnglishComment = 0
        isidfr = lambda x: x == "IDENTIFIER"
        isliteral = lambda x: x == "LITERAL"
        kindname_list = []
        tu_tokens = tu.get_tokens(extent=tu.cursor.extent)
                
        for t in tu_tokens:
            kindname_list.append(t.kind.name)
            
        length = len(kindname_list)
        
        if length == 1 and kindname_list[0] == 'PUNCTUATION':
            # Single line
            comment_text = r_t.spelling
            line, column = getlineandcolumn(r_t.location)
            
            cocode_container[filepath].append((line, column))
            
            comment_list.append(comment_text)
            continue
        if length <= 2:
            continue
        
            
        for i in range(length - 2):
            # Model: If the identifier appears three times continuously, it can be considered as an English comment block.
            # FIXME: Wrong judgment in comment "for >32 bit machines"
            if isidfr(kindname_list[i]) and isidfr(kindname_list[i+2]) and (isidfr(kindname_list[i+1]) or isliteral(kindname_list[i+1])):
                isEnglishComment = 1
                break
            elif isidfr(kindname_list[i]) and isliteral(kindname_list[i+1]) and isidfr(kindname_list[i+2]):
                isEnglishComment = 1
                break
                
        if isEnglishComment:
            continue
        
        else:
            comment_text = r_t.spelling
            line, column = getlineandcolumn(r_t.location)
            cocode_container[filepath].append((line, column))
            
            comment_list.append(comment_text)
            
    return cocode_container

        #remove_comments(filepath, comment_list)

def run(args: argparse.ArgumentParser):
    if platform.system() == "Windows":
        clang.cindex.Config.set_library_file("C:\\Program Files\\LLVM\\bin\\libclang.dll")
    elif platform.system() == "Linux":
        clang.cindex.Config.set_library_file("/usr/lib/x86_64-linux-gnu/libclang-10.so.1")
    dirname = args.dir
    filename = args.file
    dump_xmlname = args.dump_xml
    addxml_name = args.add_xml
    removecode = args.remove_cocode
    
    if dirname:
        container = {}
        sourcefileList = getfiles_fromdir(dirname)
        for sourcefile in sourcefileList:
            cocode_container = cppparser(str(sourcefile))
            container.update(cocode_container)
            
    elif filename:
        container = cppparser(filename)
    
    if dump_xmlname:
        dumpxml(dump_xmlname, container)
    
    elif addxml_name:
        addtoxml(addxml_name, container)
        
    # TODO: modify the argument transfer method.
    else:
        print("Invaild arguments. Options --help for showing help message.")
    
if __name__ == "__main__":
    argparser = argparse.ArgumentParser("Remove the comment-out cpp code")
    argparser.add_argument('--dir',
                           default='.',
                           nargs='?',
                           help="Name of directory to process."
    )
    
    argparser.add_argument('--file',
                           help="A single file to process."
    )
    argparser.add_argument('--dump_xml',
                           help="Dump the result into a xml file according to the format of cppcheck."
    )
    argparser.add_argument('--add_xml',
                            help="Add the scan result into the exists xml file."
    )
    
    argparser.add_argument('--remove_cocode',
                           help="Remove the comment-out cpp code in source file."
    )
    
    args = argparser.parse_args()
    run(args=args)