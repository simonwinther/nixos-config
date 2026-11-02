_G.migration_errors = {}
local notify = vim.notify
vim.notify = function(message, level, options)
  if level == vim.log.levels.ERROR then table.insert(_G.migration_errors, tostring(message)) end
  return notify(message, level, options)
end
-- UI plugins replace vim.notify during startup. Catch Lazy's config failures at
-- their source as well, including failures after UIEnter/VeryLazy.
vim.api.nvim_create_autocmd("User", { pattern = "LazyDone", once = true, callback = function()
  local util = require("lazy.core.util")
  local report = util.error
  util.error = function(message, options)
    table.insert(_G.migration_errors, type(message) == "table" and table.concat(message, "\n") or tostring(message))
    return report(message, options)
  end
end })
