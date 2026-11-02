-- Run only in a disposable XDG home, with the pinned Catppuccin plugin.
local ok, err = xpcall(function()
  vim.opt.rtp:prepend(assert(vim.env.NVIM_NIX_PLUGIN_ROOT) .. "/catppuccin")
  local spec = dofile(assert(vim.env.NVIM_THEME_SOURCE))[2]
  spec.config(spec, spec.opts)

  local theme = assert(vim.env.XDG_STATE_HOME) .. "/desktop/theme"
  vim.fn.mkdir(theme, "p")
  vim.api.nvim_buf_set_lines(0, 0, -1, false, { "Keep unsaved work during a theme switch" })
  local changes = 0
  vim.api.nvim_create_autocmd("ColorScheme", { callback = function() changes = changes + 1 end })
  for _, background in ipairs({ "light", "dark" }) do
    if background == "light" then
      vim.fn.writefile({}, theme .. "/light.mode")
    else
      vim.fn.delete(theme .. "/light.mode")
    end
    assert(vim.uv.kill(vim.fn.getpid(), "sigusr1") == 0)
    assert(vim.wait(2000, function() return vim.o.background == background end), "Theme reload required focus: " .. background)
    assert(vim.bo.modified, "Theme reload discarded unsaved changes")
    assert(vim.api.nvim_buf_get_lines(0, 0, -1, false)[1] == "Keep unsaved work during a theme switch")
  end
  assert(changes >= 2, "Theme reload skipped ColorScheme hooks")
  assert(vim.v.errmsg == "", vim.v.errmsg)
end, debug.traceback)
if not ok then
  print(err)
  vim.cmd("cquit 1")
else
  print("Neovim live appearance passed: light/dark signals, highlights and unsaved buffer preserved")
  vim.cmd("qa!")
end
