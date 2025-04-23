# 🎨 Omni Keywords Finder — Diretório de Assets

Este diretório contém todos os recursos visuais utilizados no sistema, organizados de forma modular e otimizada.

---

## 📁 Estrutura de Pastas

/assets/ ├── logos/ → Logotipos principais e ícones institucionais ├── icons/ → Ícones funcionais (adicionar, excluir, editar, buscar) ├── placeholders/ → Imagens de estados visuais (vazio, erro, etc.) ├── images/ → Banners, fundos, imagens decorativas


---

## ✅ Boas Práticas

- Utilize `SVG` sempre que possível (leveza e escalabilidade).
- Padronize nomes com função clara: `add.svg`, `logo_full.svg`, etc.
- Utilize `stroke=\"currentColor\"` em SVGs para herdar o tema visual.
- Prefira `width="24"` ou `32` para ícones.
- Evite `.png` e `.jpg` salvo em casos específicos — use `.webp` se necessário.
- Atente-se à acessibilidade: todos os SVGs devem ter `role="img"` e `aria-label`.

---

## 🧪 Ferramentas Recomendadas

- [SVGO](https://github.com/svg/svgo): Otimizador de SVGs
- [Squoosh](https://squoosh.app): Conversor para `.webp`
- [Vite Plugin Imagemin](https://github.com/vbenjs/vite-plugin-imagemin): Otimização automática na build

---

## 📦 Responsabilidade

O uso de assets padronizados garante:
- Melhor performance de carregamento
- Consistência visual e técnica
- Manutenção facilitada em múltiplos ambientes

---

> Última revisão: Março/2025
