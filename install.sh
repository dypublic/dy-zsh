#!/bin/bash
set -euo pipefail
umask 077

base_url='https://raw.githubusercontent.com/dypublic/dy-shell/main'
zsh_dir="${ZSH:-$HOME/.oh-my-zsh}"
custom_dir="${ZSH_CUSTOM:-$zsh_dir/custom}"
rc="${ZDOTDIR:-$HOME}/.zshrc"
theme="$custom_dir/themes/dy.zsh-theme"
tmp=$(mktemp -d "${TMPDIR:-/tmp}/dy-shell.XXXXXXXX")
trap 'rm -rf -- "$tmp"' EXIT

fetch() {
  curl -fsSL --retry 2 "$1" -o "$2"
}
fetch "$base_url/themes/dy.zsh-theme" "$tmp/dy.zsh-theme"

if test -f "$rc"; then
  cp -pL "$rc" "$tmp/base-zshrc"
else
  printf 'export ZSH=%q\nZSH_THEME="dy"\nplugins=(git)\nsource "$ZSH/oh-my-zsh.sh"\n' \
    "$zsh_dir" > "$tmp/base-zshrc"
fi

# Only replace the theme value; keep plugins and all other text.
perl - "$tmp/base-zshrc" "$tmp/zshrc" <<'PERL'
use strict;
use warnings;
my ($input, $output) = @ARGV;
open my $in, '<:raw', $input or die "$input: $!\n";
local $/;
my $text = <$in>;
my $count = () = $text =~ /^[ \t]*(?:export[ \t]+)?ZSH_THEME=/mg;
die "发现多处 ZSH_THEME，请先整理为一处。\n" if $count > 1;
if ($count) {
    $text =~ s/^([ \t]*(?:export[ \t]+)?ZSH_THEME=)("[^"\r\n]*"|'[^'\r\n]*'|[^\s#]*)([ \t]*(?:\#[^\r\n]*)?)(\r?)$/$1 . (substr($2, 0, 1) eq "'" ? "'dy'" : substr($2, 0, 1) eq '"' ? '"dy"' : 'dy') . $3 . $4/gme
        or die "无法识别 ZSH_THEME 赋值，请使用单行配置。\n";
} else {
    my $nl = $text =~ /\r\n/ ? "\r\n" : "\n";
    $text =~ s/^([ \t]*(?:source|\.)[ \t]+[^\r\n]*oh-my-zsh\.sh[^\r\n]*)(\r?)$/"ZSH_THEME=\"dy\"$nl$1$2"/me
        or die "没有找到 Oh My Zsh 加载语句，请先配置 Oh My Zsh。\n";
}
open my $out, '>:raw', $output or die "$output: $!\n";
print {$out} $text;
close $out or die "$output: $!\n";
PERL

zsh -f -o NO_BG_NICE -n "$tmp/zshrc"
zsh -f -o NO_BG_NICE -n "$tmp/dy.zsh-theme"

if ! test -f "$zsh_dir/oh-my-zsh.sh"; then
  fetch 'https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh' "$tmp/install-omz.sh"
  ZSH="$zsh_dir" KEEP_ZSHRC=yes CHSH=no RUNZSH=no \
    REPO=ohmyzsh/ohmyzsh REMOTE=https://github.com/ohmyzsh/ohmyzsh.git BRANCH=master \
    sh "$tmp/install-omz.sh" --unattended --keep-zshrc
fi

rc_changed=yes
if test -f "$rc" && cmp -s "$rc" "$tmp/zshrc"; then rc_changed=no; fi
theme_changed=yes
if test -f "$theme" && cmp -s "$theme" "$tmp/dy.zsh-theme"; then theme_changed=no; fi
if test "$rc_changed" = no && test "$theme_changed" = no; then
  printf 'dy-shell 已是最新配置，无需修改。\n'
  exit 0
fi

backup=''
backup_file() {
  test -e "$1" || return 0
  if test -z "$backup"; then
    local root="${XDG_STATE_HOME:-$HOME/.local/state}/dy-shell/backups"
    mkdir -p "$root"
    backup=$(mktemp -d "$root/$(date +%Y%m%d-%H%M%S).XXXXXXXX")
    printf '备份：%s\n' "$backup"
  fi
  cp -pL "$1" "$backup/$2"
}
if test "$rc_changed" = yes; then backup_file "$rc" zshrc; fi
if test "$theme_changed" = yes; then backup_file "$theme" dy.zsh-theme; fi

mkdir -p "$(dirname "$rc")" "$custom_dir/themes"
if test "$theme_changed" = yes; then cat "$tmp/dy.zsh-theme" > "$theme"; fi
if test "$rc_changed" = yes; then cat "$tmp/zshrc" > "$rc"; fi
printf 'dy 主题已安装，plugins 和其他配置保持不变。新开一个终端即可生效。\n'
