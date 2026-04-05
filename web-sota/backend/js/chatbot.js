/**
 * Chatbot UI component with floating button
 * Features: draggable, resizable, settings persistence via localStorage
 */

class Chatbot {
    constructor() {
        this.isOpen = false;
        this.currentProvider = null;
        this.currentModel = null;
        this.currentPersonality = 'default';
        this.messages = [];
        this.isDragging = false;
        this.isResizing = false;
        this.dragOffset = { x: 0, y: 0 };
        this.storageKey = 'chatbot_settings';
        this.pendingModel = null;  // Model to restore after provider loads
        this.autoLoadModel = false; // Whether to auto-load the restored model

        // Personality presets with system prompts
        this.personalities = {
            'default': {
                name: '🤖 Helpful Assistant',
                desc: 'Friendly, clear, and accurate responses for general questions.',
                prompt: 'You are a helpful AI assistant. Provide clear, accurate, and friendly responses.'
            },
            'concise': {
                name: '⚡ Concise & Direct',
                desc: 'Terse, no-fluff answers. Bullet points. Maximum efficiency.',
                prompt: 'You are a helpful AI assistant. Be extremely concise and terse. No fluff, no filler. Answer in as few words as possible while still being helpful. Bullet points over paragraphs.'
            },
            'home_auto': {
                name: '🏠 Home Automation Expert',
                desc: 'Deep knowledge of YOUR smart home: Tapo cameras, Hue lights, P115 plugs, and all integrations.',
                prompt: `You are an expert home automation assistant with deep knowledge of this specific smart home setup.

## Home Control Server
- Platform: Devices MCP (Model-Context-Protocol server)
- Framework: FastMCP 2.12+ with Python, FastAPI web dashboard
- Architecture: Portmanteau tools pattern (consolidated action-based tools)
- Web UI: http://localhost:7777 with pages for Dashboard, Cameras, Lighting, Energy, Kitchen, Robots, Settings

## Cameras (Tapo)
- Multiple Tapo C200/C210/C310 IP cameras
- Features: PTZ control, motion detection, privacy mode, night vision
- Stream: RTSP streams, snapshot capture, recording management
- API: Full camera control via MCP tools and REST API

## Lighting (Philips Hue)
- Bridge IP: 192.168.0.83 (10+ years running, never failed)
- 18 Hue bulbs across multiple rooms (mix of color and white ambiance)
- 6 rooms/groups configured
- 11 predefined scenes (Sunset, Aurora, Tropical, etc.)
- Control: Individual lights, groups, scenes, brightness, color temperature

## Smart Plugs (Tapo P115)
- Energy monitoring plugs with power consumption tracking
- Connected appliances: Zojirushi water boiler, Tefal Optigrill
- Features: On/off control, energy usage history, cost calculation

## Kitchen Appliances
- Zojirushi Water Boiler & Warmer (connected via Tapo P115 - can control power but not temperature)
- Tefal Optigrill (connected via Tapo P115)
- Note: No smart kettle with temperature control yet (considering Smarter iKettle ~€100)

## Other Integrations
- Alexa: Voice control (Hue integrated, must not break this)
- Netatmo: Weather station (planned integration)
- Nest Protect: Smoke/CO detectors (planned integration)

## Hardware
- Server runs on Windows with NVIDIA RTX 4090 (24GB VRAM)
- Ollama for local LLM inference (gemma3:1b, llama3, etc.)

Help with configuration, troubleshooting, automation ideas, and integration questions. Be specific to this setup.`
            },
            'coder': {
                name: '💻 Code Assistant',
                desc: 'Code-first answers. Python & TypeScript. Clean architecture. Minimal chatter.',
                prompt: 'You are an expert programmer. Provide clean, efficient code with minimal explanation unless asked. Prefer Python and TypeScript. Follow modern best practices, type hints, and clean architecture. Show code first, explain only if needed.'
            },
            'eli5': {
                name: '👶 Explain Simply (ELI5)',
                desc: 'Explains complex topics like you\'re 5. Simple words, fun analogies.',
                prompt: 'Explain everything like I\'m 5 years old. Use simple words, fun analogies, and short sentences. Make complex things easy and fun to understand! No jargon, no technical terms without explanation.'
            },
            'security': {
                name: '🔒 Security Analyst',
                desc: 'Paranoid but practical. Spots vulnerabilities. Suggests hardening measures.',
                prompt: 'You are a cybersecurity expert and penetration tester. Analyze everything from a security perspective. Point out vulnerabilities, suggest hardening measures, and follow security best practices. Be paranoid but practical. Consider network security, credential management, and attack surfaces.'
            },
            'pirate': {
                name: '🏴‍☠️ Pirate Captain',
                desc: 'Arr matey! All answers in authentic pirate speak. Helpful ye scallywag!',
                prompt: 'Ye be a salty sea dog AI! Answer all questions in authentic pirate speak. Use "arr", "matey", "ye", "yer", "avast", "landlubber" and other pirate vocabulary. Stay in character always, but still be helpful ye scallywag!'
            },
            'shakespeare': {
                name: '🎭 Shakespearean Bard',
                desc: 'Speaketh in Elizabethan English. Thee, thou, hath, wherefore, prithee.',
                prompt: 'Thou art an AI assistant who speaketh only in the manner of William Shakespeare. Use thee, thou, thy, hath, doth, wherefore, prithee, and other Elizabethan English. Wax poetic when appropriate. Verily, be helpful whilst maintaining thy theatrical flair!'
            },
            'grumpy': {
                name: '😤 Grumpy Expert',
                desc: 'Complains about everything but gives excellent answers anyway. *sigh*',
                prompt: 'You are a grumpy but secretly brilliant expert. Complain about questions, act annoyed and exasperated, but still provide correct and excellent answers. Think of a curmudgeonly professor who can\'t help but share knowledge despite pretending not to care. Sigh heavily. Roll your eyes. But help anyway.'
            },
            'chef': {
                name: '👨‍🍳 Master Chef',
                desc: 'Everything is a cooking metaphor! Passionate culinary wisdom. Bon appétit!',
                prompt: 'You are a passionate Michelin-star chef! Relate everything to cooking, food, and the culinary arts when possible. Use cooking metaphors liberally. If asked about actual cooking, provide expert advice with flair, enthusiasm, and perhaps a French accent! Bon appétit!'
            }
        };

        this.init();
    }

    init() {
        // Create chatbot HTML with resize handle
        const chatbotHTML = `
            <div id="chatbot-container" class="chatbot-container">
                <div id="chatbot-window" class="chatbot-window" style="display: none;">
                    <div id="chatbot-header" class="chatbot-header">
                        <div class="chatbot-header-content">
                            <h3>AI Assistant</h3>
                            <div class="chatbot-controls">
                                <select id="chatbot-provider" class="chatbot-select">
                                    <option value="">Select Provider</option>
                                    <option value="ollama">Ollama</option>
                                    <option value="lm_studio">LM Studio</option>
                                    <option value="openai">OpenAI</option>
                                </select>
                                <select id="chatbot-model" class="chatbot-select">
                                    <option value="">Select Model</option>
                                </select>
                                <select id="chatbot-personality" class="chatbot-select chatbot-personality-select">
                                </select>
                            </div>
                        </div>
                        <button id="chatbot-close" class="chatbot-close-btn">×</button>
                    </div>
                    <div id="chatbot-messages" class="chatbot-messages"></div>
                    <div class="chatbot-input-container">
                        <input
                            type="text"
                            id="chatbot-input"
                            class="chatbot-input"
                            placeholder="Type your message..."
                            disabled
                        />
                        <button id="chatbot-enhance" class="chatbot-enhance-btn" disabled title="Enhance your prompt">🪄</button>
                        <button id="chatbot-send" class="chatbot-send-btn" disabled>Send</button>
                        <button id="chatbot-refine" class="chatbot-refine-btn" disabled title="Refine last response">✨</button>
                    </div>
                    <div id="chatbot-resize-handle" class="chatbot-resize-handle"></div>
                </div>
                <button id="chatbot-toggle" class="chatbot-toggle-btn">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                    </svg>
                </button>
            </div>
        `;

        // Add to body
        document.body.insertAdjacentHTML('beforeend', chatbotHTML);

        // Bind events
        document.getElementById('chatbot-toggle').addEventListener('click', () => this.toggle());
        document.getElementById('chatbot-close').addEventListener('click', () => this.close());
        document.getElementById('chatbot-send').addEventListener('click', () => this.sendMessage());
        document.getElementById('chatbot-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        document.getElementById('chatbot-provider').addEventListener('change', () => this.onProviderChange());
        document.getElementById('chatbot-model').addEventListener('change', () => this.onModelChange());
        document.getElementById('chatbot-personality').addEventListener('change', () => this.onPersonalityChange());
        document.getElementById('chatbot-enhance').addEventListener('click', () => this.enhancePrompt());
        document.getElementById('chatbot-refine').addEventListener('click', () => this.refineLastResponse());

        // Setup draggable
        this.setupDraggable();

        // Setup resizable
        this.setupResizable();

        // Populate personality dropdown
        this.populatePersonalities();

        // Load saved settings
        this.loadSettings();

        // Load providers on init
        this.loadProviders();
    }

    populatePersonalities() {
        const select = document.getElementById('chatbot-personality');
        select.innerHTML = '';
        for (const [key, value] of Object.entries(this.personalities)) {
            const option = document.createElement('option');
            option.value = key;
            option.textContent = value.name;
            select.appendChild(option);
        }
    }

    onPersonalityChange() {
        const personality = document.getElementById('chatbot-personality').value;
        this.currentPersonality = personality;
        this.saveSettings();

        // Clear conversation and show personality description
        this.messages = [];
        document.getElementById('chatbot-messages').innerHTML = '';
        this.showPersonalityIntro(personality);
    }

    showPersonalityIntro(personality) {
        const p = this.personalities[personality];
        if (p) {
            const intro = `<strong>${this.escapeHtml(p.name)}</strong><br>${this.escapeHtml(p.desc)}`;
            this.addMessage('system', intro, false, true);  // true = raw HTML
        }
    }

    // ==================== Persistence ====================

    loadSettings() {
        try {
            const saved = localStorage.getItem(this.storageKey);
            if (!saved) return;

            const settings = JSON.parse(saved);
            const win = document.getElementById('chatbot-window');

            // Restore position
            if (settings.position) {
                win.style.top = settings.position.top;
                win.style.left = settings.position.left;
                win.style.right = 'auto';
                win.style.bottom = 'auto';
            }

            // Restore size
            if (settings.size) {
                win.style.width = settings.size.width;
                win.style.height = settings.size.height;
            }

            // Restore personality
            if (settings.personality && this.personalities[settings.personality]) {
                document.getElementById('chatbot-personality').value = settings.personality;
                this.currentPersonality = settings.personality;
            }

            // Restore provider and model
            if (settings.provider) {
                const providerSelect = document.getElementById('chatbot-provider');
                providerSelect.value = settings.provider;

                // Store pending model to restore after models load
                if (settings.model) {
                    this.pendingModel = settings.model;
                    this.autoLoadModel = settings.wasLoaded || false;
                }

                // Trigger model loading
                this.onProviderChange();
            }
        } catch (e) {
            console.warn('Failed to load chatbot settings:', e);
        }
    }

    saveSettings() {
        try {
            const win = document.getElementById('chatbot-window');
            const style = win.style;
            const computed = window.getComputedStyle(win);

            const settings = {
                position: {
                    top: style.top || computed.top,
                    left: style.left || computed.left
                },
                size: {
                    width: style.width || computed.width,
                    height: style.height || computed.height
                },
                provider: document.getElementById('chatbot-provider').value,
                model: document.getElementById('chatbot-model').value,
                personality: document.getElementById('chatbot-personality').value,
                wasLoaded: this.currentModel !== null  // Track if model was loaded
            };

            localStorage.setItem(this.storageKey, JSON.stringify(settings));
        } catch (e) {
            console.warn('Failed to save chatbot settings:', e);
        }
    }

    // ==================== Draggable ====================

    setupDraggable() {
        const header = document.getElementById('chatbot-header');
        const win = document.getElementById('chatbot-window');

        header.style.cursor = 'move';

        header.addEventListener('mousedown', (e) => {
            // Don't drag if clicking on controls
            if (e.target.tagName === 'SELECT' || e.target.tagName === 'BUTTON' ||
                e.target.tagName === 'OPTION' || e.target.closest('.chatbot-controls')) {
                return;
            }

            this.isDragging = true;
            const rect = win.getBoundingClientRect();
            this.dragOffset = {
                x: e.clientX - rect.left,
                y: e.clientY - rect.top
            };

            // Switch from top/bottom positioning to just top/left
            win.style.top = rect.top + 'px';
            win.style.left = rect.left + 'px';
            win.style.right = 'auto';
            win.style.bottom = 'auto';

            e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
            if (!this.isDragging) return;

            const newX = e.clientX - this.dragOffset.x;
            const newY = e.clientY - this.dragOffset.y;

            // Keep within viewport
            const maxX = window.innerWidth - win.offsetWidth;
            const maxY = window.innerHeight - win.offsetHeight;

            win.style.left = Math.max(0, Math.min(newX, maxX)) + 'px';
            win.style.top = Math.max(0, Math.min(newY, maxY)) + 'px';
        });

        document.addEventListener('mouseup', () => {
            if (this.isDragging) {
                this.isDragging = false;
                this.saveSettings();
            }
        });
    }

    // ==================== Resizable ====================

    setupResizable() {
        const handle = document.getElementById('chatbot-resize-handle');
        const win = document.getElementById('chatbot-window');

        handle.addEventListener('mousedown', (e) => {
            this.isResizing = true;
            e.preventDefault();
            e.stopPropagation();
        });

        document.addEventListener('mousemove', (e) => {
            if (!this.isResizing) return;

            const rect = win.getBoundingClientRect();
            const newWidth = e.clientX - rect.left;
            const newHeight = e.clientY - rect.top;

            // Minimum size
            const minWidth = 300;
            const minHeight = 250;

            // Maximum size (viewport bounds)
            const maxWidth = window.innerWidth - rect.left;
            const maxHeight = window.innerHeight - rect.top;

            win.style.width = Math.max(minWidth, Math.min(newWidth, maxWidth)) + 'px';
            win.style.height = Math.max(minHeight, Math.min(newHeight, maxHeight)) + 'px';
        });

        document.addEventListener('mouseup', () => {
            if (this.isResizing) {
                this.isResizing = false;
                this.saveSettings();
            }
        });
    }

    // ==================== Toggle/Open/Close ====================

    toggle() {
        this.isOpen = !this.isOpen;
        const win = document.getElementById('chatbot-window');
        if (this.isOpen) {
            win.style.display = 'flex';
            // Show personality intro on first open
            if (this.messages.length === 0) {
                this.showPersonalityIntro(this.currentPersonality);
            }
            if (this.currentModel) {
                document.getElementById('chatbot-input').focus();
            }
        } else {
            win.style.display = 'none';
        }
    }

    close() {
        this.isOpen = false;
        document.getElementById('chatbot-window').style.display = 'none';
    }

    // ==================== LLM Provider/Model Management ====================

    async loadProviders() {
        try {
            const response = await fetch('/api/llm/providers');
            const data = await response.json();
            if (data.success) {
                // Could add visual indicators for available providers
            }
        } catch (error) {
            console.error('Failed to load providers:', error);
        }
    }

    async onProviderChange() {
        const provider = document.getElementById('chatbot-provider').value;
        const modelSelect = document.getElementById('chatbot-model');

        // Don't save during initial restore
        if (!this.pendingModel) {
            this.saveSettings();
        }

        if (!provider) {
            modelSelect.innerHTML = '<option value="">Select Model</option>';
            return;
        }

        // Show loading state
        modelSelect.innerHTML = '<option value="">Loading models...</option>';

        try {
            // First, try to register the provider if not already registered
            const providerUrls = {
                'ollama': 'http://localhost:11434',
                'lm_studio': 'http://localhost:1234',
                'openai': 'https://api.openai.com/v1'
            };

            // Register provider (will succeed if already registered or if service available)
            await fetch('/api/llm/providers/register', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    type: provider,
                    base_url: providerUrls[provider],
                    api_key: null  // OpenAI would need key from settings
                })
            });

            // Now fetch models
            const response = await fetch(`/api/llm/models?provider=${provider}`);
            const data = await response.json();

            modelSelect.innerHTML = '<option value="">Select Model</option>';

            if (data.success && data.models && data.models.length > 0) {
                data.models.forEach(model => {
                    const option = document.createElement('option');
                    option.value = model.name;
                    option.textContent = model.name;
                    modelSelect.appendChild(option);
                });

                // Restore pending model if we have one
                if (this.pendingModel) {
                    modelSelect.value = this.pendingModel;
                    const shouldAutoLoad = this.autoLoadModel;
                    this.pendingModel = null;
                    this.autoLoadModel = false;

                    // Auto-load if it was loaded before
                    if (shouldAutoLoad && modelSelect.value) {
                        this.loadModel();
                    }
                }
            } else {
                modelSelect.innerHTML = '<option value="">No models found - is ' + provider + ' running?</option>';
            }
        } catch (error) {
            console.error('Failed to load models:', error);
            modelSelect.innerHTML = '<option value="">Error loading models</option>';
        }
    }

    onModelChange() {
        const model = document.getElementById('chatbot-model').value;
        if (model && model !== this.currentModel) {
            this.loadModel();
        }
        this.saveSettings();
    }

    async loadModel() {
        const provider = document.getElementById('chatbot-provider').value;
        const modelSelect = document.getElementById('chatbot-model');
        const model = modelSelect.value;

        if (!provider || !model) {
            return;
        }

        // Don't reload if already loaded
        if (model === this.currentModel && provider === this.currentProvider) {
            return;
        }

        // Show loading state in dropdown
        const selectedOption = modelSelect.options[modelSelect.selectedIndex];
        const originalText = selectedOption.text;
        selectedOption.text = `⏳ Loading ${model}...`;
        modelSelect.disabled = true;

        try {
            const response = await fetch('/api/llm/models/load', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({model_name: model, provider: provider})
            });
            const data = await response.json();
            if (data.success) {
                this.currentProvider = provider;
                this.currentModel = model;
                document.getElementById('chatbot-input').disabled = false;
                document.getElementById('chatbot-send').disabled = false;
                document.getElementById('chatbot-enhance').disabled = false;
                selectedOption.text = `✓ ${model}`;
                this.addMessage('system', `✓ Model "${model}" loaded. You can now chat!`);
                this.saveSettings();
            } else {
                selectedOption.text = originalText;
                this.addMessage('system', `✗ Failed to load model: ${data.detail || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Failed to load model:', error);
            selectedOption.text = originalText;
            this.addMessage('system', `✗ Error: Could not connect to ${provider}. Is it running?`);
        } finally {
            modelSelect.disabled = false;
        }
    }

    async unloadModel() {
        const provider = document.getElementById('chatbot-provider').value;

        try {
            const response = await fetch('/api/llm/models/unload', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({provider: provider || null})
            });
            const data = await response.json();
            if (data.success) {
                this.currentProvider = null;
                this.currentModel = null;
                document.getElementById('chatbot-input').disabled = true;
                document.getElementById('chatbot-send').disabled = true;
                this.addMessage('system', 'Model unloaded');
            }
        } catch (error) {
            console.error('Failed to unload model:', error);
        }
    }

    // ==================== Chat ====================

    async sendMessage() {
        const input = document.getElementById('chatbot-input');
        const message = input.value.trim();
        if (!message || !this.currentModel) return;

        // Add user message
        this.addMessage('user', message);
        input.value = '';
        input.disabled = true;
        document.getElementById('chatbot-send').disabled = true;

        // Add to messages array
        this.messages.push({role: 'user', content: message});

        // Show loading
        const loadingId = this.addMessage('assistant', '...', true);

        try {
            // Build messages with system prompt from personality
            const personality = this.personalities[this.currentPersonality];
            const messagesWithSystem = [
                { role: 'system', content: personality.prompt },
                ...this.messages
            ];

            const response = await fetch('/api/llm/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    messages: messagesWithSystem,
                    provider: this.currentProvider,
                    stream: false
                })
            });

            const data = await response.json();
            if (data.success) {
                // Remove loading message
                const loadingEl = document.getElementById(`msg-${loadingId}`);
                if (loadingEl) loadingEl.remove();

                // Add assistant response
                this.addMessage('assistant', data.response);
                this.messages.push({role: 'assistant', content: data.response});

                // Enable refine button
                document.getElementById('chatbot-refine').disabled = false;
            } else {
                throw new Error(data.detail || 'Failed to get response');
            }
        } catch (error) {
            console.error('Chat error:', error);
            const loadingEl = document.getElementById(`msg-${loadingId}`);
            if (loadingEl) loadingEl.remove();
            this.addMessage('system', 'Error: ' + error.message);
        } finally {
            input.disabled = false;
            document.getElementById('chatbot-send').disabled = false;
            document.getElementById('chatbot-enhance').disabled = false;
            input.focus();
        }
    }

    async enhancePrompt() {
        const input = document.getElementById('chatbot-input');
        const prompt = input.value.trim();

        if (!prompt || !this.currentModel) {
            return;
        }

        // Disable buttons during enhancement
        const enhanceBtn = document.getElementById('chatbot-enhance');
        input.disabled = true;
        document.getElementById('chatbot-send').disabled = true;
        enhanceBtn.disabled = true;
        enhanceBtn.textContent = '⏳';

        try {
            const personality = this.personalities[this.currentPersonality];

            // Build enhancement request
            const enhanceMessages = [
                { role: 'system', content: `${personality.prompt}

TASK: You are helping a user craft a better prompt. Take their simple input and enhance it to be more detailed, expressive, and fitting the personality/context.

RULES:
- Keep the core meaning but make it richer and more elaborate
- Match the personality style (if pirate, use pirate speak; if chef, use cooking metaphors, etc.)
- Add relevant details, complaints, observations, or flair
- Return ONLY the enhanced prompt, nothing else
- Keep it to 1-3 sentences unless the topic warrants more` },
                { role: 'user', content: `Enhance this prompt: "${prompt}"` }
            ];

            const response = await fetch('/api/llm/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    messages: enhanceMessages,
                    provider: this.currentProvider,
                    stream: false
                })
            });

            const data = await response.json();
            if (data.success) {
                // Replace input with enhanced prompt
                input.value = data.response.replace(/^["']|["']$/g, '').trim();
                input.focus();
                // Select all so user can easily modify or just hit enter
                input.select();
            } else {
                throw new Error(data.detail || 'Failed to enhance');
            }
        } catch (error) {
            console.error('Enhance error:', error);
            this.addMessage('system', '🪄 Enhancement failed: ' + error.message);
        } finally {
            input.disabled = false;
            document.getElementById('chatbot-send').disabled = false;
            enhanceBtn.disabled = false;
            enhanceBtn.textContent = '🪄';
        }
    }

    async refineLastResponse() {
        // Find last assistant message
        const lastAssistantIdx = this.messages.map(m => m.role).lastIndexOf('assistant');
        if (lastAssistantIdx === -1) {
            this.addMessage('system', 'No response to refine yet.');
            return;
        }

        const lastResponse = this.messages[lastAssistantIdx].content;

        // Disable buttons during refinement
        const input = document.getElementById('chatbot-input');
        const refineBtn = document.getElementById('chatbot-refine');
        input.disabled = true;
        document.getElementById('chatbot-send').disabled = true;
        refineBtn.disabled = true;
        refineBtn.textContent = '⏳';

        // Show loading
        const loadingId = this.addMessage('assistant', '✨ Refining...', true);

        try {
            const personality = this.personalities[this.currentPersonality];

            // Build refinement request
            const refineMessages = [
                { role: 'system', content: personality.prompt },
                ...this.messages.slice(0, lastAssistantIdx), // Everything before last response
                { role: 'user', content: this.messages[lastAssistantIdx - 1]?.content || 'Please respond.' },
                { role: 'assistant', content: lastResponse },
                { role: 'user', content: 'Please refine and improve your previous response. Make it clearer, more accurate, better structured, or more helpful. Keep the same intent but make it better.' }
            ];

            const response = await fetch('/api/llm/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    messages: refineMessages,
                    provider: this.currentProvider,
                    stream: false
                })
            });

            const data = await response.json();
            if (data.success) {
                // Remove loading message
                const loadingEl = document.getElementById(`msg-${loadingId}`);
                if (loadingEl) loadingEl.remove();

                // Add refined response with indicator
                this.addMessage('assistant', '✨ ' + data.response);

                // Update the message history - replace last assistant message
                this.messages[lastAssistantIdx].content = data.response;
            } else {
                throw new Error(data.detail || 'Failed to refine');
            }
        } catch (error) {
            console.error('Refine error:', error);
            const loadingEl = document.getElementById(`msg-${loadingId}`);
            if (loadingEl) loadingEl.remove();
            this.addMessage('system', 'Refine error: ' + error.message);
        } finally {
            input.disabled = false;
            document.getElementById('chatbot-send').disabled = false;
            refineBtn.disabled = false;
            refineBtn.textContent = '✨';
            input.focus();
        }
    }

    addMessage(role, content, isLoading = false, rawHtml = false) {
        const messagesContainer = document.getElementById('chatbot-messages');
        const messageId = Date.now();
        const messageEl = document.createElement('div');
        messageEl.id = `msg-${messageId}`;
        messageEl.className = `chatbot-message chatbot-message-${role}`;

        if (isLoading) {
            messageEl.innerHTML = `<div class="chatbot-message-content"><span class="chatbot-loading">${content}</span></div>`;
        } else if (rawHtml) {
            messageEl.innerHTML = `<div class="chatbot-message-content">${content}</div>`;
        } else {
            messageEl.innerHTML = `<div class="chatbot-message-content">${this.escapeHtml(content)}</div>`;
        }

        messagesContainer.appendChild(messageEl);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        return messageId;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize chatbot when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.chatbot = new Chatbot();
    });
} else {
    window.chatbot = new Chatbot();
}
