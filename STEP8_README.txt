Шаг 8 — CI (GitHub Actions)

Добавлено:
- .github/workflows/ci.yml: запускает tools/selfcheck.py на Ubuntu (push/PR для dev и main)
- requirements.txt: зависимости для selfcheck (openpyxl)

Git (dev):
  git add .github requirements.txt STEP8_README.txt
  git commit -m "chore: add CI workflow running selfcheck"
  git push
