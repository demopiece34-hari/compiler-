#!/usr/bin/env python3
"""TamilScript: a small interpreter implemented with Python's standard library only.

Syntax:
    vei name = expression
    name = expression
    sollu expression
    irunthal condition { ... } illaiyel { ... }
    thirumba condition { ... }

Operators: + - * /, == != < <= > >=, unary - and !
Strings may use single or double quotes. Newlines and semicolons separate statements.
Lines beginning with # are comments.
"""
from dataclasses import dataclass
import sys


class TamilScriptError(Exception):
    """Base class for language errors."""


class LexerError(TamilScriptError):
    pass


class ParseError(TamilScriptError):
    pass


class RuntimeErrorTS(TamilScriptError):
    pass


@dataclass(frozen=True)
class Token:
    type: str
    value: object
    line: int
    column: int


KEYWORDS = {
    "vei": "VEI",
    "sollu": "SOLL U".replace(" ", ""),
    "irunthal": "IRUNTHAL",
    "illaiyel": "ILLAIYEL",
    "thirumba": "THIRUMBA",
    "true": "BOOLEAN",
    "false": "BOOLEAN",
}


class Lexer:
    """Convert source characters into tokens."""

    TWO_CHAR = {"==": "EQEQ", "!=": "NE", "<=": "LTE", ">=": "GTE"}
    ONE_CHAR = {
        "+": "PLUS", "-": "MINUS", "*": "STAR", "/": "SLASH",
        "=": "EQUAL", "<": "LT", ">": "GT", "!": "BANG",
        "(": "LPAREN", ")": "RPAREN", "{": "LBRACE", "}": "RBRACE",
        ";": "SEMICOLON",
    }

    def __init__(self, source):
        self.source = source
        self.index = 0
        self.line = 1
        self.column = 1

    def peek(self, offset=0):
        pos = self.index + offset
        return self.source[pos] if pos < len(self.source) else "\0"

    def advance(self):
        char = self.peek()
        if char != "\0":
            self.index += 1
            if char == "\n":
                self.line += 1
                self.column = 1
            else:
                self.column += 1
        return char

    def token(self, kind, value, line, column):
        return Token(kind, value, line, column)

    def tokenize(self):
        tokens = []
        while self.peek() != "\0":
            char = self.peek()
            if char in " \t\r":
                self.advance()
            elif char == "\n":
                line, col = self.line, self.column
                self.advance()
                tokens.append(self.token("NEWLINE", "\n", line, col))
            elif char == "#":
                while self.peek() not in ("\n", "\0"):
                    self.advance()
            elif char.isdigit():
                tokens.append(self.number())
            elif char.isalpha() or char == "_":
                tokens.append(self.identifier())
            elif char in ("'", '"'):
                tokens.append(self.string())
            else:
                line, col = self.line, self.column
                pair = char + self.peek(1)
                if pair in self.TWO_CHAR:
                    self.advance()
                    self.advance()
                    tokens.append(self.token(self.TWO_CHAR[pair], pair, line, col))
                elif char in self.ONE_CHAR:
                    self.advance()
                    tokens.append(self.token(self.ONE_CHAR[char], char, line, col))
                else:
                    raise LexerError(
                        f"Unexpected character {char!r} at line {line}, column {col}"
                    )
        tokens.append(Token("EOF", None, self.line, self.column))
        return tokens

    def number(self):
        line, col, chars = self.line, self.column, []
        while self.peek().isdigit():
            chars.append(self.advance())
        if self.peek() == "." and self.peek(1).isdigit():
            chars.append(self.advance())
            while self.peek().isdigit():
                chars.append(self.advance())
        text = "".join(chars)
        value = float(text) if "." in text else int(text)
        return self.token("NUMBER", value, line, col)

    def identifier(self):
        line, col, chars = self.line, self.column, []
        while self.peek().isalnum() or self.peek() == "_":
            chars.append(self.advance())
        text = "".join(chars)
        kind = KEYWORDS.get(text, "IDENTIFIER")
        value = (text == "true") if kind == "BOOLEAN" else text
        return self.token(kind, value, line, col)

    def string(self):
        line, col = self.line, self.column
        quote = self.advance()
        chars = []
        escapes = {
            "n": "\n", "t": "\t", "r": "\r", "\\": "\\",
            "'": "'", '"': '"',
        }
        while self.peek() not in (quote, "\0"):
            char = self.advance()
            if char == "\n":
                raise LexerError(f"Unterminated string at line {line}, column {col}")
            if char == "\\":
                escaped = self.advance()
                if escaped == "\0":
                    raise LexerError(f"Unterminated escape at line {self.line}")
                chars.append(escapes.get(escaped, escaped))
            else:
                chars.append(char)
        if self.peek() == "\0":
            raise LexerError(f"Unterminated string at line {line}, column {col}")
        self.advance()
        return self.token("STRING", "".join(chars), line, col)


# AST node classes
@dataclass
class NumberNode:
    value: object


@dataclass
class StringNode:
    value: str


@dataclass
class BooleanNode:
    value: bool


@dataclass
class VariableNode:
    name: str


@dataclass
class UnaryNode:
    operator: str
    operand: object


@dataclass
class BinaryNode:
    left: object
    operator: str
    right: object


@dataclass
class VarDeclarationNode:
    name: str
    expression: object


@dataclass
class AssignmentNode:
    name: str
    expression: object


@dataclass
class PrintNode:
    expression: object


@dataclass
class IfNode:
    condition: object
    then_body: list
    else_body: object = None


@dataclass
class WhileNode:
    condition: object
    body: list


@dataclass
class ProgramNode:
    statements: list


class Parser:
    """Recursive-descent parser with conventional expression precedence."""

    def __init__(self, tokens):
        self.tokens = tokens
        self.index = 0

    def peek(self, offset=0):
        return self.tokens[min(self.index + offset, len(self.tokens) - 1)]

    def check(self, *kinds):
        return self.peek().type in kinds

    def advance(self):
        token = self.peek()
        if token.type != "EOF":
            self.index += 1
        return token

    def match(self, *kinds):
        if self.check(*kinds):
            return self.advance()
        return None

    def expect(self, kind, message):
        token = self.peek()
        if token.type != kind:
            raise ParseError(
                f"{message} at line {token.line}, column {token.column}; "
                f"found {token.type} ({token.value!r})"
            )
        return self.advance()

    def skip_separators(self):
        while self.match("NEWLINE", "SEMICOLON"):
            pass

    def parse(self):
        statements = []
        self.skip_separators()
        while not self.check("EOF"):
            statements.append(self.statement())
            if not self.check("EOF", "RBRACE", "NEWLINE", "SEMICOLON"):
                t = self.peek()
                raise ParseError(
                    f"Expected newline or ';' after statement at line {t.line}, "
                    f"column {t.column}"
                )
            self.skip_separators()
        return ProgramNode(statements)

    def statement(self):
        if self.match("VEI"):
            name = self.expect("IDENTIFIER", "Expected variable name after 'vei'").value
            self.expect("EQUAL", "Expected '=' after variable name")
            return VarDeclarationNode(name, self.expression())
        if self.match("SOLL U".replace(" ", "")):
            return PrintNode(self.expression())
        if self.match("IRUNTHAL"):
            condition = self.expression()
            then_body = self.block()
            self.skip_separators()
            else_body = self.block() if self.match("ILLAIYEL") else None
            return IfNode(condition, then_body, else_body)
        if self.match("THIRUMBA"):
            condition = self.expression()
            return WhileNode(condition, self.block())
        if self.check("IDENTIFIER") and self.peek(1).type == "EQUAL":
            name = self.advance().value
            self.advance()
            return AssignmentNode(name, self.expression())
        t = self.peek()
        raise ParseError(
            f"Expected statement at line {t.line}, column {t.column}; "
            f"found {t.type} ({t.value!r})"
        )

    def block(self):
        self.expect("LBRACE", "Expected '{' to start block")
        self.skip_separators()
        statements = []
        while not self.check("RBRACE", "EOF"):
            statements.append(self.statement())
            if not self.check("RBRACE", "NEWLINE", "SEMICOLON"):
                t = self.peek()
                raise ParseError(
                    f"Expected newline or ';' after statement at line {t.line}, "
                    f"column {t.column}"
                )
            self.skip_separators()
        self.expect("RBRACE", "Expected '}' to close block")
        return statements

    # Lowest to highest precedence: equality, comparison, +/-, */ , unary, atom.
    def expression(self):
        return self.equality()

    def equality(self):
        node = self.comparison()
        while self.match("EQEQ", "NE"):
            op = self.tokens[self.index - 1].value
            node = BinaryNode(node, op, self.comparison())
        return node

    def comparison(self):
        node = self.term()
        while self.match("LT", "LTE", "GT", "GTE"):
            op = self.tokens[self.index - 1].value
            node = BinaryNode(node, op, self.term())
        return node

    def term(self):
        node = self.factor()
        while self.match("PLUS", "MINUS"):
            op = self.tokens[self.index - 1].value
            node = BinaryNode(node, op, self.factor())
        return node

    def factor(self):
        node = self.unary()
        while self.match("STAR", "SLASH"):
            op = self.tokens[self.index - 1].value
            node = BinaryNode(node, op, self.unary())
        return node

    def unary(self):
        if self.match("MINUS", "BANG"):
            op = self.tokens[self.index - 1].value
            return UnaryNode(op, self.unary())
        return self.primary()

    def primary(self):
        token = self.peek()
        if self.match("NUMBER"):
            return NumberNode(token.value)
        if self.match("STRING"):
            return StringNode(token.value)
        if self.match("BOOLEAN"):
            return BooleanNode(token.value)
        if self.match("IDENTIFIER"):
            return VariableNode(token.value)
        if self.match("LPAREN"):
            node = self.expression()
            self.expect("RPAREN", "Expected ')' after expression")
            return node
        raise ParseError(
            f"Expected value or expression at line {token.line}, "
            f"column {token.column}; found {token.type} ({token.value!r})"
        )


class Interpreter:
    """Execute AST nodes and store declared variables in an environment."""

    MAX_LOOP_ITERATIONS = 1_000_000

    def __init__(self, output_function=print):
        self.environment = {}
        self.output = output_function

    def run(self, program):
        for statement in program.statements:
            self.execute(statement)

    def execute_block(self, statements):
        for statement in statements:
            self.execute(statement)

    def execute(self, node):
        if isinstance(node, VarDeclarationNode):
            if node.name in self.environment:
                raise RuntimeErrorTS(f"Variable '{node.name}' is already declared")
            self.environment[node.name] = self.evaluate(node.expression)
        elif isinstance(node, AssignmentNode):
            if node.name not in self.environment:
                raise RuntimeErrorTS(f"Undefined variable '{node.name}'")
            self.environment[node.name] = self.evaluate(node.expression)
        elif isinstance(node, PrintNode):
            self.output(self.evaluate(node.expression))
        elif isinstance(node, IfNode):
            if self.truthy(self.evaluate(node.condition)):
                self.execute_block(node.then_body)
            elif node.else_body is not None:
                self.execute_block(node.else_body)
        elif isinstance(node, WhileNode):
            iterations = 0
            while self.truthy(self.evaluate(node.condition)):
                iterations += 1
                if iterations > self.MAX_LOOP_ITERATIONS:
                    raise RuntimeErrorTS(
                        f"Loop exceeded safety limit of {self.MAX_LOOP_ITERATIONS:,} iterations"
                    )
                self.execute_block(node.body)
        else:
            raise RuntimeErrorTS(f"Unknown statement node: {type(node).__name__}")

    def evaluate(self, node):
        if isinstance(node, (NumberNode, StringNode, BooleanNode)):
            return node.value
        if isinstance(node, VariableNode):
            if node.name not in self.environment:
                raise RuntimeErrorTS(f"Undefined variable '{node.name}'")
            return self.environment[node.name]
        if isinstance(node, UnaryNode):
            value = self.evaluate(node.operand)
            if node.operator == "-":
                if not self.is_number(value):
                    raise RuntimeErrorTS("Unary '-' requires a number")
                return -value
            if node.operator == "!":
                return not self.truthy(value)
        if isinstance(node, BinaryNode):
            left = self.evaluate(node.left)
            right = self.evaluate(node.right)
            op = node.operator
            if op == "+":
                if isinstance(left, str) and isinstance(right, str):
                    return left + right
                if self.is_number(left) and self.is_number(right):
                    return left + right
                raise RuntimeErrorTS("'+' requires two numbers or two strings")
            if op in ("-", "*", "/"):
                if not self.is_number(left) or not self.is_number(right):
                    raise RuntimeErrorTS(f"'{op}' requires numeric operands")
                if op == "-":
                    return left - right
                if op == "*":
                    return left * right
                if right == 0:
                    raise RuntimeErrorTS("Division by zero")
                return left / right
            if op == "==":
                return left == right
            if op == "!=":
                return left != right
            if op in ("<", "<=", ">", ">="):
                valid = type(left) is type(right) and (
                    self.is_number(left) or isinstance(left, str)
                )
                if not valid:
                    raise RuntimeErrorTS(
                        f"'{op}' requires values of the same numeric or string type"
                    )
                if op == "<":
                    return left < right
                if op == "<=":
                    return left <= right
                if op == ">":
                    return left > right
                return left >= right
        raise RuntimeErrorTS(f"Unknown expression node: {type(node).__name__}")

    @staticmethod
    def is_number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    @staticmethod
    def truthy(value):
        return bool(value)


def run_tamilscript(source, output_function=print):
    """Lex, parse, and execute TamilScript source code."""
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    Interpreter(output_function=output_function).run(ast)


TEST_PROGRAM = r"""
# Test variables, strings, arithmetic, if/else, and loops.
vei peyar = "TamilScript"
vei a = 10
vei b = 3
vei total = a + b * 2

sollu "Vanakkam from " + peyar
sollu "Math result (10 + 3 * 2) ="
sollu total
sollu "Subtraction ="
sollu a - b
sollu "Multiplication ="
sollu a * b
sollu "Division ="
sollu a / b

irunthal total > 15 {
    sollu "If branch: total is greater than 15"
} illaiyel {
    sollu "Else branch: total is 15 or less"
}

vei count = 1
thirumba count <= 3 {
    sollu "Loop count:"
    sollu count
    count = count + 1
}

sollu "Test program finished."
"""


def main():
    try:
        if len(sys.argv) > 1:
            with open(sys.argv[1], "r", encoding="utf-8") as source_file:
                source = source_file.read()
        else:
            source = TEST_PROGRAM
        run_tamilscript(source)
    except (LexerError, ParseError, RuntimeErrorTS) as error:
        print(f"TamilScript error: {error}", file=sys.stderr)
        sys.exit(1)
    except OSError as error:
        print(f"Could not read source file: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
