from deproc.core import LanguagePlugin
from .linker import PythonLinker
from .resolver import PythonResolver
from .parser import PythonSourceParser
from .symbol_cache import PythonSymbolCache
from .symbol_table_builder import PythonSymbolTableBuilder

PythonPlugin = LanguagePlugin(
    language="python",
    aliases=["py"],
    file_extensions=[".py", ".pyi"],
    linker=PythonLinker(),
    resolver=PythonResolver(),
    source_parser=PythonSourceParser(),
    symbol_cache=PythonSymbolCache(),
    symbol_table_builder=PythonSymbolTableBuilder()
)