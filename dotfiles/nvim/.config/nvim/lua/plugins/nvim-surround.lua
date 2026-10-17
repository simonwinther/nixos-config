-- ~/.config/nvim/lua/plugins/nvim-surround.lua
return {
  {
    "kylechui/nvim-surround",
    version = "*",
    event = "VeryLazy",
    config = function()
      require("nvim-surround").setup({
        -- keep defaults; you can add custom behavior later if needed
      })
    end,
  },
}
