# Agente Mentor

O arquivo `system_prompt.txt` contém o System Prompt oficial fornecido no enunciado,
sem alterações. O chat de terminal em `chat.py` usa esse prompt como instrução de
sistema e conversa com o LLM da Abacus RouteLLM:

```bash
python -m src.mentor.chat                     # conversa interativa
python -m src.mentor.chat --uma "pergunta"    # uma pergunta e sai
```

Configuração, uso e um exemplo real de pergunta e resposta: [docs/mentor.md](../../docs/mentor.md).
