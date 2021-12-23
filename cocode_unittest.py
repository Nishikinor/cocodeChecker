
import clang.cindex
import cocode
import os

if "CLANG_LIBRARY_PATH" in os.environ:
    clang.cindex.Config.set_library_file(os.environ["CLANG_LIBRARY_PATH"])


def get_tokens(comment_content):
    idx_comment = clang.cindex.Index.create()
    c_tu = idx_comment.parse('tmp.cpp',
                        args = ["-std=c++11"],
                        unsaved_files=[('tmp.cpp', comment_content)],
                        options=0
    )
    c_tokens = c_tu.get_tokens(extent=c_tu.cursor.extent)
    return c_tokens


class TestFilter:
    def test_comment_parser(self):
        filter1 = cocode.Filter("tests/test_filter.cpp")
        filter1.getcomments()
        container = filter1.container
        tokenlist = list(container.values())
        token1, token2 = tokenlist[0]
        
        expect_content1 = " test comment 1"
        expect_content2 = " const char* string = \"teststring\";"
        comment_content1 = filter1.comment_parser(token1)
        comment_content2 = filter1.comment_parser(token2)
        assert comment_content1 == expect_content1
        assert comment_content2 == expect_content2
    
    def test_vaild_code(self):
        filter2 = cocode.Filter("tests/test_filter.cpp")
        # refcnt += 1, filter2 is a reference to filter1, so we don't need to call getcomments method again.
        container = filter2.container
        except_vaild1 = False
        except_vaild2 = True
        tokenlist = list(container.values())
        token1, token2 = tokenlist[0]
        comment_content1 = filter2.comment_parser(token1)
        comment_content2 = filter2.comment_parser(token2)
        c_tokens1 = get_tokens(comment_content1)
        c_tokens2 = get_tokens(comment_content2)
        
        assert filter2.isvaildcode(c_tokens1) == except_vaild1
        assert filter2.isvaildcode(c_tokens2) == except_vaild2