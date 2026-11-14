# dy-shell

我的 Oh My Zsh 主题，适用于 macOS 和 Linux。直接下载必要文件，无需 fork 或 clone 本仓库。

## 安装 / 更新

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/dypublic/dy-shell/main/install.sh)"
```

安装和更新使用同一条命令，完成后新开终端即可。需要 Bash、Zsh、Perl、curl；首次安装官方 Oh My Zsh 还需要 Git。

## 脚本做什么

- 下载 `dy` 主题到 `~/.oh-my-zsh/custom/themes/dy.zsh-theme`。
- 将 `.zshrc` 的 `ZSH_THEME` 改为 `dy`；没有这项时，在加载 Oh My Zsh 前插入。
- **保留现有 plugins 和其他配置。** 不替换整份 `.zshrc`，不创建 `.zshrc.local`。
- 未安装 Oh My Zsh 时安装官方版本，不使用 sudo，也不更改默认 shell。

主题显示用户名、主机名、当前目录和 Git 分支；工作区有改动时显示红色 `⚡`。

## 备份

修改前先检查 Zsh 语法，并将会被覆盖的已有文件备份到：

```text
~/.local/state/dy-shell/backups/<时间>.<随机后缀>/
```

备份目录会在安装时打印。配置已经一致时跳过，不重复备份。已有符号链接保留，更新写入目标文件。

脚本面向常规的单行 `ZSH_THEME` 配置；多处赋值需要先整理为一处。没有 `.zshrc` 时创建最小配置。

非默认安装目录可通过导出的 `ZSH`、`ZSH_CUSTOM`、`ZDOTDIR` 指定；备份位置支持 `XDG_STATE_HOME`。

## 官方 Oh My Zsh 更新

官方框架独立更新：

```zsh
omz update
```

## 测试

```bash
python3 -m unittest discover -s tests -v
```

CI 在 Linux 和 macOS 上运行测试，并验证官方 Oh My Zsh 的实际安装。
