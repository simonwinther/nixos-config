local ls = require("luasnip")
local s = ls.snippet
local t = ls.text_node
local i = ls.insert_node
local fmt = require("luasnip.extras.fmt").fmt

return {
  s(
    "main",
    fmt(
      [[
#include <bits/stdc++.h>
using namespace std;

int main() {{
  ios::sync_with_stdio(0);
  cin.tie(0);

  {}
  return 0;
}}
]],
      { i(1, "// code here") }
    )
  ),
}
