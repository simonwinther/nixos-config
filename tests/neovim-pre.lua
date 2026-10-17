_G.migration_errors = {}
local notify = vim.notify
vim.notify = function(message, level, options)
  if level == vim.log.levels.ERROR then table.insert(_G.migration_errors, tostring(message)) end
  return notify(message, level, options)
end
