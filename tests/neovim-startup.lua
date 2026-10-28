vim.api.nvim_create_autocmd("VimEnter", { once = true, callback = function()
  vim.defer_fn(function()
    local ok, err = xpcall(function()
      assert(vim.deep_equal(vim.g.root_spec, { "cwd" }), "Picker roots must follow the working directory")
      require("lazyvim.config").load("keymaps")
      for _, key in ipairs({ "/", "sg" }) do
        local mapping = vim.fn.maparg((vim.g.mapleader or "\\") .. key, "n", false, true)
        assert(mapping.desc == "Grep (cwd)", "Missing working-directory grep shortcut: " .. key)
      end
      require("lazy").load({ plugins = { "LuaSnip", "blink.cmp", "nvim-treesitter" } })
      assert(type(require("luasnip")) == "table")
      assert(type(require("blink.cmp")) == "table")
      local native = assert(package.loadlib(vim.env.NVIM_NIX_PLUGIN_ROOT .. "/blink.cmp/target/release/libblink_cmp_fuzzy.so", "luaopen_blink_cmp_fuzzy"))
      assert(type(native()) == "table")
      assert(LazyVim.treesitter.have("lua"), "LazyVim did not discover the Nix parsers")
      local specs = vim.json.decode(table.concat(vim.fn.readfile(vim.env.NVIM_MIGRATION_PARSER_MANIFEST), "\n"))
      local languages = vim.tbl_map(function(spec) return spec.name end, specs)
      for _, lang in ipairs(languages) do
        assert(vim.treesitter.language.add(lang), "Missing parser: " .. lang)
      end
      for lang, text in pairs({ lua = "local value = 1", python = "value = 1\n", c = "int main(void) { return 0; }", latex = [[\documentclass{article}\begin{document}Hello\end{document}]], typst = "= Hello\n" }) do
        local parser = vim.treesitter.get_string_parser(text, lang)
        local trees = parser:parse()
        assert(#trees > 0 and not trees[1]:root():has_error(), "Parser rejected sample: " .. lang)
      end
      assert(vim.v.errmsg == "", vim.v.errmsg)
      assert(#_G.migration_errors == 0, table.concat(_G.migration_errors, "\n"))
      print("Migration Neovim smoke passed: startup, LuaSnip, completion setup, " .. #languages .. " parsers, five sample parses")
    end, debug.traceback)
    if not ok then
      print(err)
      vim.cmd("cquit 1")
    else
      vim.cmd("qa!")
    end
  end, 2000)
end })
