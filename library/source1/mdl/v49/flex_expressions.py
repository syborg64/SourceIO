class Value:
    def __hash__(self):
        return hash(self.value)

    def __eq__(self, o: object) -> bool:
        if isinstance(o, self.__class__):
            o: Value
            return self.value == o.value
        else:
            return False

    def __init__(self, value, ):
        self.value = value

    def __repr__(self):
        return f'{self.value:.4}'

    def as_simple(self):
        return str(self)


class Neg(Value):
    def __repr__(self):
        return f'(-{self.value})'


class FetchController(Value):

    def __init__(self, value, stereo=False):
        self.stereo = stereo
        super().__init__(value)

    def __repr__(self):
        return f'{self.value.replace(" ", "_")}'

    def as_simple(self):
        name = f'{self.value.replace(" ", "_")}'
        if self.stereo and name.startswith('right_'):
            name = name[6:]
        if self.stereo and name.startswith('left_'):
            name = name[5:]
        return name


class FetchFlex(Value):
    def __repr__(self):
        return f'{self.value.replace(" ", "_")}'

    def as_simple(self):
        return f'{self.value.replace(" ", "_")}'


class Expr:
    def __hash__(self) -> int:
        return hash(self.left) + hash(self.right)

    def __eq__(self, o: object) -> bool:
        if isinstance(o, self.__class__):
            o: Expr
            return self.left == o.left and self.right == o.right
        else:
            return False

    def __init__(self, lhs, rhs, ):
        self.left = lhs
        self.right = rhs

    def as_simple(self):
        arg1 = self.left.as_simple()
        arg2 = self.right.as_simple()
        return f'({arg1} + {arg2})'


class Add(Expr):
    def __repr__(self):
        arg1 = self.left if isinstance(self.left, (Value, Function)) else f'({self.left})'
        arg2 = self.right if isinstance(self.right, (Value, Function)) else f'({self.right})'
        return f'{arg1} + {arg2}'


class Sub(Expr):
    def __repr__(self):
        arg1 = self.left if isinstance(self.left, (Value, Function)) else f'({self.left})'
        arg2 = self.right if isinstance(self.right, (Value, Function)) else f'({self.right})'
        return f'{arg2} - {arg1}'


class Mul(Expr):
    def __repr__(self):
        arg1 = self.left if isinstance(self.left, (Value, Function)) else f'({self.left})'
        arg2 = self.right if isinstance(self.right, (Value, Function)) else f'({self.right})'
        return f'{arg1}*{arg2}'


class Div(Expr):
    def __repr__(self):
        arg1 = self.left if isinstance(self.left, (Value, Function)) else f'({self.left})'
        arg2 = self.right if isinstance(self.right, (Value, Function)) else f'({self.right})'
        return f'{arg1}/{arg2}'


class Function:
    def __hash__(self) -> int:
        return hash(sum(map(hash, self.values)))

    def __eq__(self, o: object) -> bool:
        if isinstance(o, self.__class__):
            o: Function
            return len(self.values) == len(o.values) and all(a == b for (a, b) in zip(self.values, o.values))
        else:
            return False

    def __init__(self, *values):
        self.values: list = list(values)

    def as_simple(self):
        return "Implement me"


class CustomFunction(Function):
    def __init__(self, function_name: str, *values):
        super().__init__(*values)
        self.function_name = function_name

    def __repr__(self) -> str:
        return f'{self.function_name}({", ".join(map(str, self.values))})'


class RClamp(Function):
    def as_simple(self):
        return f'RemapValClamped({self.values[0].as_simple()}, {self.values[1]}, {self.values[2]}, {self.values[3]}, {self.values[4]})'

    def __repr__(self) -> str:
        return f'rclamped({self.values[0]}, {self.values[1]}, {self.values[2]}, {self.values[3]}, {self.values[4]})'


class Clamp(Function):
    def as_simple(self):
        return f'min(max({self.values[0].as_simple()}, {self.values[1]}), {self.values[2]})'

    def __repr__(self) -> str:
        return f'clamp({self.values[0]},{self.values[1]},{self.values[2]})'


class NWay(Function):

    def __init__(self, *values):
        super().__init__(*values)

    def as_simple(self):
        multi_cnt, flex_cnt, f_x, f_y, f_z, f_w = self.values
        multi_cnt = multi_cnt.as_simple()
        flex_cnt = flex_cnt.as_simple()
        greater_than_x = f"min(1, (-min(0, ({f_x} - {multi_cnt} ))))"
        less_than_y = f"min(1, (-min(0, ({multi_cnt} - ({f_y})))))"
        remap_x = f"min(max(({flex_cnt} - {f_x}) / ({f_y} - ({f_x}) ), 0), 1)"
        greater_than_equal_y = f"-(min(1, (-min(0, ({multi_cnt} - ({f_y}))))) - 1)"
        less_than_equal_z = f"-(min(1, (-min(0, ({f_z} - {multi_cnt})))) - 1)"
        greater_than_z = f"min(1, (-min(0, ({f_z} - {multi_cnt}))))"
        less_than_w = f"min(1, (-min(0, ({multi_cnt} - ({f_w})))))"
        remap_z = f"(1 - (min(max(({multi_cnt} - ({f_z})) / ({f_w} - ({f_z})), 0), 1)))"

        fl_value = f"(({greater_than_x} * {less_than_y}) * {remap_x}) + ({greater_than_equal_y} * {less_than_equal_z}) + (({greater_than_z} * {less_than_w}) * {remap_z})"

        return f"(({fl_value}) * ({flex_cnt}))"
        # return f'NWay({self.values[0]},{self.values[1]},{self.values[2]},{self.values[3]},{self.values[4], {self.values[5]} })'

    def __repr__(self) -> str:
        return f'nway({self.values[0]},{self.values[1]},{self.values[2]},{self.values[3]},{self.values[4], {self.values[5]} })'


class Max(Function):
    def __repr__(self):
        arg1 = self.values[0] if isinstance(self.values[0], Value) else f'({self.values[0]})'
        arg2 = self.values[1] if isinstance(self.values[1], Value) else f'({self.values[1]})'
        return f'max({arg1},{arg2})'

    def as_simple(self):
        arg1 = self.values[0] if isinstance(self.values[0], Value) else f'({self.values[0]})'
        arg2 = self.values[1] if isinstance(self.values[1], Value) else f'({self.values[1]})'
        return f'max({arg1.as_simple()},{arg2.as_simple()})'


class Min(Function):
    def __repr__(self):
        arg1 = self.values[0] if isinstance(self.values[0], Value) else f'({self.values[0]})'
        arg2 = self.values[1] if isinstance(self.values[1], Value) else f'({self.values[1]})'

        return f'min({arg1},{arg2})'

    def as_simple(self):
        arg1 = self.values[0] if isinstance(self.values[0], Value) else f'({self.values[0]})'
        arg2 = self.values[1] if isinstance(self.values[1], Value) else f'({self.values[1]})'
        return f'min({arg1.as_simple()},{arg2.as_simple()})'


class Combo(Function):
    def __repr__(self):
        return f'combo({", ".join(map(str, self.values))})'

    def as_simple(self):
        return f'({"*".join(map(lambda x: x.as_simple(), self.values))})'


class Dominator(Function):
    def __repr__(self):
        return f'dom({self.values[0]}, {", ".join(map(str, self.values[1:]))})'

    def as_simple(self):
        return f'((1 - {self.values[-1].as_simple()}) * {"*".join(map(lambda x: x.as_simple(), self.values[:-1]))})'
