# Design — Esteira GUT

O sistema visual da aplicação. Toda tela lê este arquivo antes de ganhar código. Para mudar o
sistema, altere este arquivo e `tokens.css` juntos; uma tela não inventa a própria exceção.

A fonte dos valores é `esteira/boards/static/boards/css/tokens.css`. As regras que dá para verificar
por máquina estão em `esteira/tests/boards/test_design_system.py`.

## Para quem

Uma pessoa que usa a esteira várias vezes por dia para decidir o que fazer agora, e que pode ser
neurodivergente (TDAH, autismo, dislexia). Isso define quatro prioridades, nesta ordem:

1. **Uma coisa pede atenção por vez.** A tarefa em execução é a única com a barra vermelha.
2. **Nada se mexe sozinho.** Sem animação de entrada, sem aviso que some, sem contagem regressiva.
3. **Tudo tem nome escrito.** Nenhuma ação depende só de ícone, cor ou posição.
4. **Errar não custa caro.** Descartar se desfaz; excluir avisa antes. Concluir não se desfaz, mas
   nada se perde: a tarefa fica em "Concluídas".

## Genre

Editorial, tratado como aplicação: papel, tinta, fios e tipografia. Sem cartões, sem sombras, sem
degradês, sem ícones decorativos.

## Macrostructure family

- Páginas de aplicação (as duas esteiras): **Index-First**. A fila é um índice numerado pela
  prioridade; a nota é a figura de cada linha. Acima de 60rem, duas colunas (5fr / 7fr): à esquerda
  o que você faz agora e o formulário, à direita a fila.
- Página de conteúdo (revisão semanal): **Stat-Led**. Um número real grande e, abaixo, listas com fio.
- Páginas de formulário (entrar, editar sem JavaScript): coluna única estreita, só o formulário.
- Navegação **N1a** (marca à esquerda, links de texto à direita): são só dois destinos e a saída.
- Rodapé **Ft2**: uma frase, sem links.

## Theme

Tema sob medida. Humor: calmo, legível, com fios, um único vermelho de sinal. Um matiz âncora
quente (60 a 85°) tinge todos os neutros; o vermelho é o único acento.

| Token | Claro | Escuro | Para quê |
| --- | --- | --- | --- |
| `--color-paper` | `oklch(96.5% 0.012 85)` | `oklch(19% 0.012 70)` | fundo da página |
| `--color-paper-2` | `oklch(93.5% 0.014 85)` | `oklch(23% 0.014 70)` | fundo do aviso de regra e do botão sob o ponteiro |
| `--color-field` | `oklch(98.8% 0.006 85)` | `oklch(15.5% 0.01 70)` | fundo dos campos |
| `--color-rule` | `oklch(80% 0.014 80)` | `oklch(36% 0.012 70)` | fio entre linhas (decorativo) |
| `--color-edge` | `oklch(52% 0.014 75)` | `oklch(62% 0.012 75)` | borda de campo e de botão |
| `--color-muted` | `oklch(42% 0.014 70)` | `oklch(76% 0.012 80)` | texto secundário |
| `--color-ink` | `oklch(22% 0.012 60)` | `oklch(92% 0.01 85)` | texto, botão principal, foco |
| `--color-ink-2` | `oklch(32% 0.012 60)` | `oklch(84% 0.01 85)` | texto de apoio |
| `--color-accent` | `oklch(50% 0.18 28)` | `oklch(72% 0.15 28)` | "precisa de você agora" |
| `--color-accent-ink` | `var(--color-paper)` | idem | texto sobre o acento |
| `--color-focus` | `var(--color-ink)` | idem | contorno de foco |

O papel é creme, e não branco puro, e a tinta é um preto suave: contraste alto sem ofuscar.

**Onde o vermelho aparece, e só aí:** a barra sobre a tarefa em execução, a marca de "Fazer já" e de
"Crise", prazo vencido ou que vence hoje, e erro de formulário (a mensagem e a borda do campo).
Sempre junto de palavras; nunca é a cor sozinha que informa.

Contraste medido (WCAG 2, claro / escuro): tinta sobre papel 15,7 / 14,6; texto secundário 7,7 / 8,6;
vermelho sobre papel 5,9 / 7,0; borda de campo 5,0 / 5,1. O fio entre linhas (1,7) é decorativo: a
separação também vem do espaço.

## Typography

- Display: Atkinson Hyperlegible Next, peso 800, estilo normal.
- Body: Atkinson Hyperlegible Next, peso 400 (350 no tema escuro), negrito 700.
- Mono: Atkinson Hyperlegible Mono, só na linha da conta (`G5 × U5 × T4 = 100 ÷ 2`).
- Tracking: corpo `0.005em`, display `-0.015em`.
- Escala: `--text-sm` 0,9375rem · `--text-base` 1,0625rem (17 px) · `--text-md` 1,3125rem ·
  `--text-lg` 1,625rem · `--text-xl` clamp(2rem, 1.4rem + 2.6vw, 2.75rem) ·
  `--text-figure` clamp(3rem, 2rem + 6vw, 4.5rem).
- Entrelinha 1,55 no corpo e 1,2 nos títulos; medida máxima de 60 caracteres.
- Números com `tabular-nums`, na face de texto.

A família foi desenhada pelo Braille Institute para que letras e algarismos parecidos não se
confundam (I, l e 1; O e 0; b e d). As fontes ficam no próprio servidor (a CSP proíbe origem
externa), com alternativas ajustadas às mesmas métricas para o texto não pular quando elas chegam.

Proibido em qualquer tela: texto todo em maiúsculas, itálico, texto justificado, texto abaixo de
15 px.

## Spacing

Escala de 4 pontos com nome, em `tokens.css`: `--space-3xs` 2 px · `2xs` 4 · `xs` 8 · `sm` 12 ·
`md` 16 · `lg` 24 · `xl` 40 · `2xl` 64 · `3xl` 96. As telas usam o nome, nunca o valor.

Estrutura por fios, não por caixas: 1 px entre linhas, 2 px de tinta acima de cada seção, 4 px de
vermelho acima da tarefa em execução. Raio 0 nos blocos e 4 px nos campos e botões.

Alvos de toque: campos com 48 px de altura, ações de texto com no mínimo 44 × 44 px.

Texto dentro de campo nunca é cortado: cada opção de lista cabe no campo fechado a 320 px. Por isso
as descrições das escalas são curtas, e dois campos só ficam lado a lado quando há 11,5rem para
cada um.

## Motion

- Só os indicadores de requisição se movem: a barra do topo e o giro dentro do controle acionado.
- Nenhuma revelação ao rolar, nenhuma transição de entrada, nenhum número que conta até o valor.
- Uma única transição de estado: a cor de fundo do botão, em 120 ms.
- `prefers-reduced-motion`: a barra fica parada e cheia, o giro desacelera para 3 s, as transições
  somem.
- Curvas: `--ease-out` cubic-bezier(0.16, 1, 0.3, 1) · `--ease-in` cubic-bezier(0.7, 0, 0.84, 0) ·
  `--ease-in-out` cubic-bezier(0.65, 0, 0.35, 1).

## Microinteractions stance

- **Toda requisição mostra status** (regra do projeto, em `CLAUDE.md`). A barra do topo aparece na
  hora e fica pelo menos 300 ms, para que uma resposta instantânea seja um pulso calmo e não um
  piscar. O controle acionado é desabilitado na hora. O giro dentro dele só aparece se a resposta
  passar de 150 ms, em um espaço já reservado, para o texto não se deslocar.
- **Sucesso é silencioso.** A tela muda; não há aviso de "salvo".
- **A resposta aparece onde você está olhando.** Uma ação recusada pela regra mostra a mensagem no
  topo da esteira, e a tela rola até ela. Falha de rede ou do servidor fica em um aviso fixo até
  você fechar. Toda mensagem diz o que aconteceu e o que fazer. Nada some sozinho.
- **O foco do teclado acompanha a resposta:** vai para a mensagem, para o campo com erro, para o
  formulário que abriu ou para o título da seção onde você agiu. Nunca volta para o topo da página.
- **Desfazer em vez de confirmar.** Descartar não pergunta: a tarefa vai para "Descartadas", com
  "Restaurar". Só a exclusão da clássica pergunta, porque lá não há volta.
- **O formulário não pula.** Cada campo tem uma linha reservada para a mensagem de erro, e toda
  mensagem cabe nessa linha em um celular de 320 px. As mensagens são nossas, nunca o balão do
  navegador.
- Foco: contorno de 3 px em tinta, afastado 2 px, em todo elemento interativo.
- A primeira parada do teclado em toda página é "Pular para o conteúdo".
- Painéis abertos continuam abertos depois que a esteira é atualizada.

## CTA voice

- Principal: fundo em tinta, texto em papel, 48 px de altura, raio 4 px, peso 700. Verbo mais
  objeto, sem ponto: "Iniciar a próxima", "Adicionar à fila", "Concluir tarefa". Uma por seção.
- Secundária: mesmo formato, só com borda. "Devolver à fila", "Cancelar".
- Ação de texto: sublinhada, peso 700. "Editar", "Descartar", "Restaurar". Reticências quando a
  ação abre uma pergunta antes de acontecer: "Pausar…", "Bloquear…".
- Redação literal. Sem metáfora, sem exclamação, sem jargão. O mesmo nome para a mesma coisa em
  toda tela.

## Per-page allowances

- Nenhuma página usa ilustração, imagem de fundo ou enriquecimento. A função carrega a tela.
- As esteiras podem mostrar a figura da nota em cada linha da fila; a revisão semanal pode mostrar
  um número grande, desde que seja um dado real da pessoa.
- Páginas de formulário: só tipografia e campos.

## What pages MUST share

- A marca "Esteira GUT" em texto, no mesmo lugar.
- O vermelho e os quatro lugares onde ele aparece.
- A família tipográfica e a escala.
- O formato dos botões e das ações de texto.
- O título de seção: fio de 2 px em tinta, título em peso 800, uma coluna só.
- Rótulo visível acima de todo campo; nunca só o texto de exemplo dentro dele.

## What pages MAY differ on

- A macroestrutura, dentro da família acima.
- O que a linha da fila mostra: a clássica mostra a faixa e as três notas; a aprimorada mostra a
  conta inteira, o esforço e o tempo de espera.
- Seções presentes: Pausadas, Bloqueadas e Descartadas só existem na aprimorada.

## Deviations from Hallmark defaults

Cada uma é escolha, não descuido.

| Padrão do Hallmark | Aqui | Por quê |
| --- | --- | --- |
| Foco na cor do acento | Foco em tinta | O vermelho quer dizer uma coisa só: "precisa de você agora" |
| Display e corpo de famílias diferentes | Uma superfamília | Formas de letra constantes cansam menos quem tem dislexia |
| Tracking de display bem negativo | `-0.015em` | Letras apertadas se confundem |
| Rótulos pequenos em maiúsculas | Nenhum | Maiúsculas tiram a forma da palavra |
| Número que conta até o valor | Parado | Nada se mexe sozinho |
| Itálico para ênfase no corpo | Negrito | Itálico é mais difícil de ler |

## Sources

As orientações de acessibilidade cognitiva são consenso de especialistas e de pessoas usuárias, não
resultado de ensaio controlado. As referências completas estão em
[`docs/auditoria.md`](docs/auditoria.md), números 25 a 27.

| Decisão | Fonte |
| --- | --- |
| Uma ação principal por seção; rótulos visíveis; redação literal; desfazer; nada some sozinho | W3C, *Making Content Usable for People with Cognitive and Learning Disabilities* (25) |
| Cores simples, linguagem direta, botões descritivos, layout previsível | GOV.UK, cartazes de acessibilidade: autismo e dislexia (26) |
| Fonte sem serifa, corpo maior, entrelinha ampla, sem itálico nem maiúsculas, fundo creme | Ako Aotearoa, *Dyslexia-friendly style guide* (27) |

## Exports

`tokens.css` é a fonte. Os outros formatos são traduções, para reaproveitar o sistema em outro
projeto; este projeto não usa Tailwind nem shadcn.

### tokens.css

```css
:root {
  --color-paper:      oklch(96.5% 0.012 85);
  --color-paper-2:    oklch(93.5% 0.014 85);
  --color-field:      oklch(98.8% 0.006 85);
  --color-rule:       oklch(80% 0.014 80);
  --color-edge:       oklch(52% 0.014 75);
  --color-muted:      oklch(42% 0.014 70);
  --color-ink:        oklch(22% 0.012 60);
  --color-ink-2:      oklch(32% 0.012 60);
  --color-accent:     oklch(50% 0.18 28);
  --color-accent-ink: var(--color-paper);
  --color-focus:      var(--color-ink);

  --font-display: "Atkinson Hyperlegible Next", "Esteira Sans Fallback", sans-serif;
  --font-body:    "Atkinson Hyperlegible Next", "Esteira Sans Fallback", sans-serif;
  --font-outlier: "Atkinson Hyperlegible Mono", "Esteira Mono Fallback", monospace;

  --space-3xs: 0.125rem; --space-2xs: 0.25rem; --space-xs: 0.5rem;
  --space-sm:  0.75rem;  --space-md:  1rem;    --space-lg: 1.5rem;
  --space-xl:  2.5rem;   --space-2xl: 4rem;    --space-3xl: 6rem;

  --text-sm: 0.9375rem; --text-base: 1.0625rem; --text-md: 1.3125rem;
  --text-lg: 1.625rem;  --text-xl: clamp(2rem, 1.4rem + 2.6vw, 2.75rem);

  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --dur-micro: 120ms; --dur-short: 220ms; --dur-long: 420ms;
  --radius-card: 0; --radius-input: 4px;
}
```

### Tailwind v4 `@theme`

```css
@theme {
  --color-paper:   oklch(96.5% 0.012 85);
  --color-paper-2: oklch(93.5% 0.014 85);
  --color-field:   oklch(98.8% 0.006 85);
  --color-rule:    oklch(80% 0.014 80);
  --color-edge:    oklch(52% 0.014 75);
  --color-muted:   oklch(42% 0.014 70);
  --color-ink:     oklch(22% 0.012 60);
  --color-ink-2:   oklch(32% 0.012 60);
  --color-accent:  oklch(50% 0.18 28);

  --font-display: "Atkinson Hyperlegible Next", sans-serif;
  --font-body:    "Atkinson Hyperlegible Next", sans-serif;
  --font-outlier: "Atkinson Hyperlegible Mono", monospace;

  --spacing-3xs: 0.125rem; --spacing-2xs: 0.25rem; --spacing-xs: 0.5rem;
  --spacing-sm:  0.75rem;  --spacing-md:  1rem;    --spacing-lg: 1.5rem;
  --spacing-xl:  2.5rem;   --spacing-2xl: 4rem;    --spacing-3xl: 6rem;

  --text-sm: 0.9375rem; --text-base: 1.0625rem; --text-md: 1.3125rem; --text-lg: 1.625rem;

  --radius-card: 0; --radius-input: 4px;
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
}
```

### DTCG `tokens.json`

```json
{
  "color": {
    "paper":   { "$value": "oklch(96.5% 0.012 85)", "$type": "color" },
    "paper-2": { "$value": "oklch(93.5% 0.014 85)", "$type": "color" },
    "field":   { "$value": "oklch(98.8% 0.006 85)", "$type": "color" },
    "rule":    { "$value": "oklch(80% 0.014 80)",   "$type": "color" },
    "edge":    { "$value": "oklch(52% 0.014 75)",   "$type": "color" },
    "muted":   { "$value": "oklch(42% 0.014 70)",   "$type": "color" },
    "ink":     { "$value": "oklch(22% 0.012 60)",   "$type": "color" },
    "ink-2":   { "$value": "oklch(32% 0.012 60)",   "$type": "color" },
    "accent":  { "$value": "oklch(50% 0.18 28)",    "$type": "color" }
  },
  "font": {
    "display": { "$value": "Atkinson Hyperlegible Next, sans-serif", "$type": "fontFamily" },
    "body":    { "$value": "Atkinson Hyperlegible Next, sans-serif", "$type": "fontFamily" },
    "outlier": { "$value": "Atkinson Hyperlegible Mono, monospace",  "$type": "fontFamily" }
  },
  "size": {
    "text-sm":     { "$value": "0.9375rem", "$type": "dimension" },
    "text-base":   { "$value": "1.0625rem", "$type": "dimension" },
    "text-md":     { "$value": "1.3125rem", "$type": "dimension" },
    "text-lg":     { "$value": "1.625rem",  "$type": "dimension" },
    "text-xl":     { "$value": "2.75rem",   "$type": "dimension" },
    "text-figure": { "$value": "4.5rem",    "$type": "dimension" }
  },
  "space": {
    "3xs": { "$value": "0.125rem", "$type": "dimension" },
    "2xs": { "$value": "0.25rem",  "$type": "dimension" },
    "xs":  { "$value": "0.5rem",   "$type": "dimension" },
    "sm":  { "$value": "0.75rem",  "$type": "dimension" },
    "md":  { "$value": "1rem",     "$type": "dimension" },
    "lg":  { "$value": "1.5rem",   "$type": "dimension" },
    "xl":  { "$value": "2.5rem",   "$type": "dimension" },
    "2xl": { "$value": "4rem",     "$type": "dimension" },
    "3xl": { "$value": "6rem",     "$type": "dimension" }
  },
  "duration": {
    "micro": { "$value": "120ms", "$type": "duration" },
    "short": { "$value": "220ms", "$type": "duration" },
    "long":  { "$value": "420ms", "$type": "duration" }
  }
}
```

### shadcn/ui CSS variables

```css
:root {
  --background:             96.5% 0.012 85;   /* paper */
  --foreground:             22%   0.012 60;   /* ink */
  --card:                   96.5% 0.012 85;   /* paper: there are no cards */
  --card-foreground:        22%   0.012 60;
  --popover:                93.5% 0.014 85;   /* paper-2 */
  --popover-foreground:     22%   0.012 60;
  --primary:                22%   0.012 60;   /* ink: the main button is ink, not red */
  --primary-foreground:     96.5% 0.012 85;
  --secondary:              93.5% 0.014 85;   /* paper-2 */
  --secondary-foreground:   32%   0.012 60;   /* ink-2 */
  --muted:                  93.5% 0.014 85;   /* paper-2 */
  --muted-foreground:       42%   0.014 70;   /* muted */
  --accent:                 93.5% 0.014 85;   /* shadcn uses this for hover fills */
  --accent-foreground:      22%   0.012 60;
  --destructive:            50%   0.18  28;   /* signal red */
  --destructive-foreground: 96.5% 0.012 85;
  --border:                 80%   0.014 80;   /* rule */
  --input:                  52%   0.014 75;   /* edge */
  --ring:                   22%   0.012 60;   /* focus */
  --radius:                 4px;
}
```
