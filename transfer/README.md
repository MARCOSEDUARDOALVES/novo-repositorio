# Exporting the repository without GitHub access

> **Git Bash quick copy:**
> ```bash
> base64 -d work.bundle.b64.txt > work.bundle
> git clone work.bundle novo-repositorio
> cd novo-repositorio
> git checkout work
> git remote add origin https://github.com/MARCOSEDUARDOALVES/novo-repositorio.git
> git push -u origin work
> ```
> Run the lines above in Git Bash after downloading/copying the bundle
> file. They restore the `work` branch locally and push it straight to
> your GitHub repository.

> **Resumo em português:** Execute `python export_repository_bundle.py --skip-zip --print-base64 --base64-output transfer/work.bundle.b64.txt`. Baixe ou copie o arquivo `transfer/work.bundle.b64.txt`, converta-o em `work.bundle` com `base64 -d`, clone o bundle e faça `git push` para o seu repositório no GitHub. O passo a passo detalhado segue abaixo em inglês.

When the Codex sandbox cannot reach GitHub, use `export_repository_bundle.py` to
copy the full repository history and the working directory snapshot out of the
environment.

## 1. Generate the artifacts

```bash
python export_repository_bundle.py --skip-zip --print-base64 --base64-output transfer/work.bundle.b64.txt
```

This command creates:

- `transfer/work.bundle` – a Git bundle with the entire history of the `work`
  branch.
- `transfer/work.bundle.b64.txt` – a Base64 text representation ready to copy when
  direct downloads are blocked.
- *(Optional)* `transfer/worktree_snapshot.zip` – drop `--skip-zip` if you also
  want the working tree snapshot.

## 2. Restore the work on your computer

1. **Create the bundle locally**

   Save the Base64 output between the markers into a file (for example,
   `bundle.b64`) and decode it:

   ```bash
   base64 -d bundle.b64 > work.bundle
   ```

   Alternatively, if you can download `transfer/work.bundle` directly, skip the
   Base64 step.

2. **Re-create the repository history**

   ```bash
   git clone work.bundle novo-repositorio
   cd novo-repositorio
   git checkout work
   ```

3. **Restore the working tree snapshot (optional)**

   Extract the ZIP next to the cloned repository if you also copied the
   `worktree_snapshot.zip` file:

   ```bash
   unzip worktree_snapshot.zip -d novo-repositorio
   ```

   This step refreshes the working directory with the exact files that were
   present in the sandbox.

4. **Add your GitHub remote and push**

   ```bash
   git remote add origin https://github.com/MARCOSEDUARDOALVES/novo-repositorio.git
   git push -u origin work
   ```

After pushing, GitHub will contain the full history and files from the Codex
environment so nothing is lost.

## 3. When GitHub refuses to update the PR automatically

If you open an existing Pull Request and GitHub shows the banner
`O Codex atualmente não permite atualizar PRs que foram modificados fora dele.
Por enquanto, crie um novo PR.`, it simply means that the Codex sandbox cannot
refresh that PR for you.

The fix is to push the branch from your computer (steps above) and then open a
fresh PR manually:

1. Visit <https://github.com/MARCOSEDUARDOALVES/novo-repositorio>.
2. Click **Pull requests ▸ New pull request**.
3. Use `main` as the base branch (or the branch you want to merge into) and
   select `work` as the compare branch.
4. Review the diff and submit with **Create pull request**.

The new PR will contain the entire history restored from the bundle, even though
the old one could not be updated inside Codex.
