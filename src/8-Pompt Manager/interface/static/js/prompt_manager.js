document.addEventListener("DOMContentLoaded", async function () {
    showLoader();
    await loadPrompts();
    hideLoader();
});

const API_PROMPTS_URL = "/api/prompts";
const PROMPT_CACHE_KEY = "prompt_cache";
const CACHE_EXPIRATION = 300000; // 5 minutos
const ITEMS_PER_PAGE = 10;
let currentPage = 1;

function showLoader() {
    document.getElementById("loader").style.display = "block";
}

function hideLoader() {
    document.getElementById("loader").style.display = "none";
}

async function fetchWithCache(url, cacheKey) {
    const cachedData = sessionStorage.getItem(cacheKey);
    if (cachedData) {
        const { timestamp, data } = JSON.parse(cachedData);
        if (Date.now() - timestamp < CACHE_EXPIRATION) {
            return data;
        }
    }
    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error("Erro ao buscar dados");
        const data = await response.json();
        sessionStorage.setItem(cacheKey, JSON.stringify({ timestamp: Date.now(), data }));
        return data;
    } catch (error) {
        console.error("Erro ao carregar prompts:", error);
        showError("Falha ao carregar prompts. Tente novamente mais tarde.");
        return [];
    }
}

async function loadPrompts() {
    const prompts = await fetchWithCache(API_PROMPTS_URL, PROMPT_CACHE_KEY);
    displayPrompts(prompts);
}

function displayPrompts(prompts) {
    const promptsContainer = document.getElementById("prompts-list");
    promptsContainer.innerHTML = "";
    
    const fragment = document.createDocumentFragment();
    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    const end = start + ITEMS_PER_PAGE;
    const paginatedPrompts = prompts.slice(start, end);
    
    paginatedPrompts.forEach(prompt => {
        const promptItem = document.createElement("div");
        promptItem.classList.add("prompt-item");
        promptItem.textContent = prompt.texto;
        promptItem.setAttribute("aria-label", `Prompt: ${prompt.texto}`);
        promptItem.setAttribute("tabindex", "0");
        fragment.appendChild(promptItem);
    });
    promptsContainer.appendChild(fragment);
    updatePaginationControls(prompts.length);
}

function updatePaginationControls(totalItems) {
    const paginationContainer = document.getElementById("pagination-controls");
    paginationContainer.innerHTML = "";
    
    const totalPages = Math.ceil(totalItems / ITEMS_PER_PAGE);
    for (let i = 1; i <= totalPages; i++) {
        const pageButton = document.createElement("button");
        pageButton.textContent = i;
        pageButton.setAttribute("aria-label", `Página ${i}`);
        pageButton.onclick = () => {
            currentPage = i;
            loadPrompts();
        };
        paginationContainer.appendChild(pageButton);
    }
}

function filterPrompts() {
    const searchQuery = document.getElementById("search-box").value.toLowerCase();
    const allPrompts = JSON.parse(sessionStorage.getItem(PROMPT_CACHE_KEY)).data || [];
    const filteredPrompts = allPrompts.filter(prompt => prompt.texto.toLowerCase().includes(searchQuery));
    displayPrompts(filteredPrompts);
}

document.getElementById("search-box").addEventListener("input", filterPrompts);

function showError(message) {
    const errorContainer = document.getElementById("error-message");
    errorContainer.textContent = message;
    errorContainer.style.display = "block";
}

async function listenForPromptUpdates() {
    const socket = new WebSocket("ws://localhost:8000/ws/prompts");
    socket.onmessage = async function () {
        console.log("📡 Atualização recebida dos prompts.");
        sessionStorage.removeItem(PROMPT_CACHE_KEY);
        await loadPrompts();
    };
}

listenForPromptUpdates();

document.getElementById("prompts-form").addEventListener("submit", async function (event) {
    event.preventDefault();
    const selectedPrompt = document.getElementById("prompts-list").value;
    if (!selectedPrompt) {
        showError("Por favor, selecione um prompt válido.");
        return;
    }
    console.log("Prompt selecionado:", selectedPrompt);
});
