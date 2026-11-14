import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dy-zsh-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.omz = self.root / "omz"
        self.omz.mkdir()
        (self.omz / "oh-my-zsh.sh").write_text("# fixture\n")
        self.zdot = self.root / "zdot"
        self.zdot.mkdir()
        self.rc = self.zdot / ".zshrc"
        self.theme = self.omz / "custom/themes/dy.zsh-theme"
        self.state = self.root / "state"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        curl = self.bin / "curl"
        curl.write_text('''#!/bin/bash
set -eu
url=''
out=''
while [ "$#" -gt 0 ]; do
  case "$1" in
    -o) out="$2"; shift 2 ;;
    https://*) url="$1"; shift ;;
    *) shift ;;
  esac
done
case "$url" in
  */themes/dy.zsh-theme)
    test "${TEST_FAIL_DOWNLOAD:-}" != yes || exit 22
    cp "$TEST_THEME" "$out"
    ;;
  */ohmyzsh/ohmyzsh/master/tools/install.sh)
    cp "$TEST_OFFICIAL_INSTALLER" "$out"
    ;;
  *) exit 99 ;;
esac
''')
        curl.chmod(0o755)
        self.env = dict(os.environ)
        for key in ("ZSH", "ZSH_CUSTOM"):
            self.env.pop(key, None)
        self.env.update(
            PATH=f"{self.bin}:/usr/bin:/bin:/usr/sbin:/sbin",
            ZSH=str(self.omz),
            ZDOTDIR=str(self.zdot),
            XDG_STATE_HOME=str(self.state),
            TEST_THEME=str(ROOT / "themes/dy.zsh-theme"),
        )

    def config(self, body='ZSH_THEME="old"\n', end="\n"):
        return f'export ZSH="{self.omz}"\n' + body + 'source "$ZSH/oh-my-zsh.sh"' + end

    def run_installer(self, success=True):
        result = subprocess.run(
            ["/bin/bash", str(ROOT / "install.sh")],
            env=self.env, text=True, capture_output=True, timeout=30,
        )
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def backups(self):
        return list((self.state / "dy-zsh/backups").glob("*"))

    def test_preserves_everything_but_theme_and_is_idempotent(self):
        original = self.config(
            '# ZSH_THEME="example"\nexport ZSH_THEME=\'old\'  # keep this\n'
            'plugins=(\n  git\n  python\n  docker\n)\n'
            'export KEEP_ME="hello world"\nalias ll="ls -la"\n'
        )
        self.rc.write_text(original)
        self.rc.chmod(0o640)
        self.run_installer()
        self.assertEqual(self.rc.read_text(), original.replace("ZSH_THEME='old'", "ZSH_THEME='dy'"))
        self.assertEqual(self.rc.stat().st_mode & 0o777, 0o640)
        self.assertEqual(self.theme.read_bytes(), (ROOT / "themes/dy.zsh-theme").read_bytes())
        self.assertEqual(len(self.backups()), 1)
        self.assertEqual((self.backups()[0] / "zshrc").read_text(), original)
        self.assertEqual(self.backups()[0].stat().st_mode & 0o777, 0o700)
        self.run_installer()
        self.assertEqual(len(self.backups()), 1)

    def test_missing_theme_inserted_before_source_without_changing_plugins(self):
        original = self.config('plugins=(git npm)\n', end="")
        self.rc.write_text(original)
        self.run_installer()
        self.assertEqual(self.rc.read_text(), original.replace('source ', 'ZSH_THEME="dy"\nsource ', 1))

    def test_crlf_and_unquoted_theme_preserved(self):
        original = self.config('ZSH_THEME=old\nplugins=(git npm)\n').replace("\n", "\r\n").encode()
        self.rc.write_bytes(original)
        self.run_installer()
        self.assertEqual(self.rc.read_bytes(), original.replace(b"ZSH_THEME=old", b"ZSH_THEME=dy"))

    def test_multiple_theme_assignments_stop_without_changes(self):
        original = self.config('ZSH_THEME="one"\nZSH_THEME="two"\n')
        self.rc.write_text(original)
        self.run_installer(success=False)
        self.assertEqual(self.rc.read_text(), original)
        self.assertFalse(self.theme.exists())
        self.assertEqual(self.backups(), [])

    def test_syntax_error_or_download_failure_does_not_modify_files(self):
        original = self.config() + 'if\n'
        self.rc.write_text(original)
        self.run_installer(success=False)
        self.assertEqual(self.rc.read_text(), original)
        self.assertFalse(self.theme.exists())
        self.rc.write_text(self.config())
        self.env['TEST_FAIL_DOWNLOAD'] = 'yes'
        self.run_installer(success=False)
        self.assertEqual(self.rc.read_text(), self.config())
        self.assertEqual(self.backups(), [])

    def test_existing_theme_backup_and_preserve_symlinks(self):
        target = self.root / "managed-zshrc"
        original = self.config()
        target.write_text(original)
        self.rc.symlink_to(target)
        self.theme.parent.mkdir(parents=True)
        theme_target = self.root / "managed-theme"
        theme_target.write_text("# previous theme\n")
        self.theme.symlink_to(theme_target)
        self.run_installer()
        self.assertTrue(self.rc.is_symlink())
        self.assertTrue(self.theme.is_symlink())
        self.assertEqual(target.read_text(), original.replace('ZSH_THEME="old"', 'ZSH_THEME="dy"'))
        self.assertEqual((self.backups()[0] / "dy.zsh-theme").read_text(), "# previous theme\n")

    def test_custom_directory_and_path_with_spaces(self):
        custom = self.root / "my custom"
        self.env['ZSH_CUSTOM'] = str(custom)
        original = self.config(f'ZSH_CUSTOM="{custom}"\nZSH_THEME="old"\nplugins=(git npm)\n')
        self.rc.write_text(original)
        self.run_installer()
        self.assertTrue((custom / "themes/dy.zsh-theme").is_file())
        self.assertFalse(self.theme.exists())
        self.assertIn('plugins=(git npm)', self.rc.read_text())

    def test_new_zshrc_and_missing_official_framework(self):
        shutil.rmtree(self.omz)
        official = self.root / "official-installer"
        official.write_text('''#!/bin/sh
set -eu
test "$KEEP_ZSHRC" = yes
test "$CHSH" = no
test "$RUNZSH" = no
test "$REPO" = ohmyzsh/ohmyzsh
test "$REMOTE" = https://github.com/ohmyzsh/ohmyzsh.git
mkdir -p "$ZSH"
printf '# official fixture\\n' > "$ZSH/oh-my-zsh.sh"
''')
        self.env['TEST_OFFICIAL_INSTALLER'] = str(official)
        self.run_installer()
        self.assertTrue((self.omz / "oh-my-zsh.sh").exists())
        self.assertIn('ZSH_THEME="dy"', self.rc.read_text())
        self.assertIn('plugins=(git)', self.rc.read_text())
        self.assertEqual(self.backups(), [])


if __name__ == "__main__":
    unittest.main()
