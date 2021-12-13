import pathlib
import clang.cindex
import re
import argparse
import xml.etree.ElementTree as ET

def getfiles_fromdir(dirname, extensions={'.cpp', '.hpp', '.cc', '.h', 'cxx', 'c'}):
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
    param filepath: Source code filepath
    param comment_list: List of comments to be removed from source code.
    '''
    with open(filepath, 'r') as filehandle:
        file_content = filehandle.read()
    
    with open(filepath, 'w') as wfilehandle:
        for comment_text in comment_list:
            if "\r\n" in comment_text:
                comment_text = comment_text.replace('\r\n', '\n')
            file_content = file_content.replace(comment_text, '')
            
        wfilehandle.write(file_content)

def dumpxml(xmlname):
    '''TODO:Dump the xml file according to the format of cppcheck
    '''
    
    
    
    
def addtoxml(xmlname):
    '''TODO:Add the content to a exists xml file according to the format of cppcheck
    '''
    
    if not pathlib.exists(xmlname):
        raise FileNotFoundError(f"Can't find the xml file: {xmlname}")
    
    
    
    
def writexml(xmlname, mode):
    pass

def cppparser(filepath):
    idx = clang.cindex.Index.create()
    raw_tu = idx.parse(filepath, args=['-std=c++11'])
    raw_tu_tokens = raw_tu.get_tokens(extent=raw_tu.cursor.extent)
    zh_cn_pattern = r"[\u4e00-\u9fa5]"
    comment_list = []
    
    for r_t in raw_tu_tokens:
        if r_t.kind.name != "COMMENT":
            continue
        
        print(f"t_kindname: {r_t.kind.name}, t_spelling: {r_t.spelling}")
        print("-------------------------------------------------\n")
        comment_content = r_t.spelling
        zhcn_match = re.search(zh_cn_pattern, comment_content)
        if zhcn_match:
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
            #print(f"t_kindname = {t.kind.name}, t_spelling = {t.spelling}")
            
        length = len(kindname_list)
        
        if length == 1 and kindname_list[0] == 'PUNCTUATION':
            comment_text = r_t.spelling
            comment_list.append(comment_text)
        
        
        if length <= 2:
            continue
        
            
        for i in range(length - 2):
            # Model: If the identifier appears three times continuously, it can be considered as an English comment block.
            # FIXME: Wrong judgment in comment "for >32 bit machines"
            #        Error check in block code comment
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
            comment_list.append(comment_text)
        

                    
    
def run(args):
    clang.cindex.Config.set_library_file("libclang.dll")
    dirname = args.dirname
    filename = args.filename
    dumpxml = args.dump_xml
    addxml = args.add_xml
    removecode = args.remove_cocode
    
    if dirname:
        sourcefileList = getfiles_fromdir(dirname)
        for sourcefile in sourcefileList:
            cppparser(sourcefile)
    elif filename:
        cppparser(filename)
        
    

if __name__ == "__main__":
    argparser = argparse.ArgumentParser("Remove the comment-out cpp code")
    argparser.add_argument('--dir',
                           default='tests',
                           nargs='?',
                           help="Name of directory for us to process."
    )
    
    argparser.add_argument('--file',
                           help="A single file for us to process."
    )
    argparser.add_argument('--dump_xml',
                           default="result.xml",
                           nargs='?',
                           help="Dump the result into a xml file according to the format of cppcheck."
    )
    argparser.add_argument('--add_xml',
                            default="cppcheck.xml",
                            nargs='?',
                            help="Add the scan result into the exists xml file."
    )
    
    argparser.add_argument('--remove_cocode',
                           help="Remove the comment-out cpp code in source file."
    )
    
    args = argparser.parse_args()
    run(args=args)