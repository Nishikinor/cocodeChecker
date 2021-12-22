import pathlib
import clang.cindex
import argparse
import xml.etree.ElementTree as ET
import sys
import re
from xml.dom import minidom
from collections import defaultdict
from lxml import etree

CocodeContainer = defaultdict(list) # k-v type: {filename: list[token]}

class Filter:
    """
    Extract the required sequence according to the specified rules, 
    you can customize the rules in this class to extract the sequence what you need.
    """
    
    def __init__(self, filename, container=defaultdict(list)):
        self.filename = filename
        self.idx = clang.cindex.Index.create()
        self.tu = self.idx.parse(filename, args=["-std=c++11"])
        self.tokens = self.tu.get_tokens(extent=self.tu.cursor.extent)
        self.container = container # list of result tokens
    
    def getcomments(self):
        """Get all comments from the source file.
        """
        for token in self.tokens:
            if token.kind.name == "COMMENT":
                self.container[self.filename].append(token)
        
                        
    
    def isvaildcode(self, c_tokens):
        """return True if the comment contains vaild code Section.
        """
        isidfr = lambda x: x == "IDENTIFIER"
        isliteral = lambda x: x == "LITERAL"
        
        kindname_list = []
        c_tokenlist = []
        available = [';', '{', '}', '[', ']', '(', ')']
        for c_t in c_tokens:
            kindname_list.append(c_t.kind.name)
            c_tokenlist.append(c_t)
        
        tokens_length = len(c_tokenlist)
        if tokens_length == 1:
            if kindname_list[0] == "PUNCTUATION":
                return 1
            else:
                return 0
            
        if tokens_length <= 2:
            return 0
        
        for i in range(tokens_length - 2):
            # Model: If the identifier appears three times continuously, it can be considered as an English comment block.
            if isidfr(kindname_list[i]) and isidfr(kindname_list[i+2]) and (isidfr(kindname_list[i+1]) or isliteral(kindname_list[i+1])):
                return 0
            
        finalchar = c_tokenlist[-1]
        #finalchar = c_tokenlist[-1]
        
        if finalchar.spelling not in available:
            return 0
        
        return 1
    
    
    def CommentedOutcode(self):
        "filter the commented-out code in self.container"
        self.getcomments()
  
        temp = list(self.container.items())
        removelist = []
        filterfunc_remove = lambda x: x not in removelist
        
        for filename, tokenlist in temp:
            for token in tokenlist:
                try:
                    comment_content = token.spelling
                except UnicodeDecodeError: 
                    removelist.append(token)
                    continue
            
                noascii_match = re.match(r"[^\x00-\x7f]", comment_content, flags=re.UNICODE | re.IGNORECASE)
                if noascii_match:
                    removelist.append(token)
                    continue
                if "copyright" in comment_content.lower():
                    removelist.append(token)
                    continue
                
                if comment_content.startswith('//'):
                    comment_content = comment_content.lstrip('//')
            
                if comment_content.startswith("/*"):
                    comment_content = comment_content.lstrip("/*")
                    comment_content = comment_content.rstrip("*/")
                
                idx_comment = clang.cindex.Index.create()
                c_tu = idx_comment.parse('tmp.cpp',
                                        args=['-std=c++11'], 
                                        unsaved_files=[('tmp.cpp', comment_content)],
                                        options=0
                )
                c_tu_tokens = c_tu.get_tokens(extent=c_tu.cursor.extent)
                
                if not self.isvaildcode(c_tu_tokens):
                    removelist.append(token)
                    
            self.container[filename] = list(filter(filterfunc_remove, self.container[filename]))
                
class XMLProcessor:
    def __init__(self, container: CocodeContainer):
        self.container = container      # CocodeContainer: {filepath: list[token]}
        self.root = None                # ET.Element
    
    def generate_childnodes(self, node):
        """Generates child nodes from the given root node and container.
        param root: ET.Element
        param container: CocodeContainer
        """
        global args
        err_attr = {
            "id": "CommentedoutCode",
            "severity": "style",
            "msg": "Section of code should not be commented out.",
            "verbose": "Section of code should not be commented out."
        }
        
        for filepath, tokenlist in self.container.items():
            if args.dir:
                # mode: dir
                dirpath = pathlib.Path(args.dir)
                filepath = pathlib.Path(filepath)
                filepath = filepath.relative_to(dirpath)

            for token in tokenlist:
                line = token.location.line
                column = token.location.column
                loc_attr = {
                    "file": str(filepath),
                    'line': str(line),
                    'column': str(column),
                }
                for errors in node.iter("errors"):
                    new_error = ET.SubElement(errors, "error", err_attr)
                    ET.SubElement(new_error, "location", loc_attr)
    
    def writefmtxml(self, xmlname, node):
        '''Save the formatted xml document by indentation spaces.
        param xmlname: Str, the name of the xml file to write.
        param root: ET.Element, root Element
        '''
        
        pretty_xml = minidom.parseString(ET.tostring(node)).toprettyxml(indent="    ", newl="\r")
        with open(xmlname, "wb") as f:
            f.write(pretty_xml.encode('utf-8'))
            
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(xmlname, parser)
        tree.write(xmlname, pretty_print=True, encoding="utf-8")

            
    def addtoxml(self, xmlname: str):
        '''Add the content to a exists xml file according to the format of cppcheck
        param xmlname: Str, the name of the xml file to write.
        param container: CocodeContainer.
        '''
        xmlfile = pathlib.Path(xmlname)
        
        if not xmlfile.exists():
            raise FileNotFoundError(f"Can't find the xml file: {xmlname}")
        
        tree = ET.parse(xmlname)
        self.root = tree.getroot()
        
        self.generate_childnodes(self.root)
        self.writefmtxml(xmlname, self.root)
        
        
    def dumpxml(self, xmlname: str):
        '''Dump the xml file according to the format of cppcheck
        param xmlname: Str, the name of the xml file to write.
        param container: CocodeContainer.
        '''
        xmlfile = pathlib.Path(xmlname)
        if xmlfile.exists():
            raise OSError(f"The {xmlname} file already exists, Please change the name of dump file or remove the file with the same name.")
        
        result = ET.Element("results", attrib={"version":"2"})
        ET.SubElement(result, "cppcheck", attrib={"version":"1.90"})    #DONE: fixed cppcheck element lack problem
        ET.SubElement(result, "errors")

        self.generate_childnodes(result)
        self.writefmtxml(xmlname, result)

def getfiles_fromdir(dirname, extensions={'.cpp', '.hpp', '.cc', '.h', 'cxx', 'c'}):
    '''Get cpp source files from directory
    param dirname: Str, the name of the input directory.
    Returns: list[Pathobj]
    '''
    p = pathlib.Path(dirname)
    filelist = []
    for path in p.glob(r'**/*'):
        if path.suffix in extensions:
            filelist.append(path)
    
    return filelist


def run(args: argparse.ArgumentParser):
    sys.path.append(".")
    from config import libclang_path
    clang.cindex.Config.set_library_file(libclang_path)

    dirname = args.dir
    filename = args.file
    dump_xmlname = args.dump_xml
    addxml_name = args.add_xml
    
    if dirname:
        sourcefileList = getfiles_fromdir(dirname)
        
        container = defaultdict(list)
        for sourcepath in sourcefileList:
            filter = Filter(str(sourcepath), container)
            filter.CommentedOutcode()
            container = filter.container
         
    elif filename:
        filter = Filter(filename)
        filter.CommentedOutcode()
        container = filter.container
    
    xmlprocessor = XMLProcessor(container)
    if dump_xmlname:
        xmlprocessor.dumpxml(dump_xmlname)
    
    elif addxml_name:
        xmlprocessor.addtoxml(addxml_name)
                
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