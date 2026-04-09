class NarratorService {
    constructor() {
        this.synth = window.speechSynthesis;
        this.activeUtterance = null;
        // Warm up voices
        if (this.synth) {
            this.synth.getVoices();
        }
    }

    // A web-audio synthesized "Walkie Talkie" ping/squelch sound
    async playPing() {
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = ctx.createOscillator();
            const gainNode = ctx.createGain();

            osc.type = 'square';
            osc.frequency.setValueAtTime(800, ctx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(300, ctx.currentTime + 0.1);
            
            gainNode.gain.setValueAtTime(0.5, ctx.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.1);

            osc.connect(gainNode);
            gainNode.connect(ctx.destination);

            osc.start();
            osc.stop(ctx.currentTime + 0.1);

            // Give it a brief moment before resolving
            return new Promise(resolve => setTimeout(resolve, 600));
        } catch (e) {
            console.warn("Could not play ping sound", e);
            return Promise.resolve();
        }
    }

    async speak(text, onEndCallback) {
        if (!this.synth) return;

        // Cancel anything currently playing
        this.synth.cancel();

        // Play the walkie talkie ping FIRST
        await this.playPing();

        this.activeUtterance = new SpeechSynthesisUtterance(text);
        this.activeUtterance.rate = 0.85; 
        this.activeUtterance.pitch = 0.95; 

        // Premium story-telling voice matching from earlier logic
        const voices = this.synth.getVoices();
        const preferredVoices = ['Samantha', 'Karen', 'Daniel', 'Moira', 'Google US English', 'Google UK English Female'];
        let selectedVoice = null;
        for (const name of preferredVoices) {
            selectedVoice = voices.find(v => v.name.includes(name));
            if (selectedVoice) break;
        }
        if (!selectedVoice) {
            selectedVoice = voices.find(v => v.lang.startsWith('en-'));
        }
        if (selectedVoice) {
            this.activeUtterance.voice = selectedVoice;
        }

        this.activeUtterance.onend = () => {
            if (onEndCallback) onEndCallback();
            this.activeUtterance = null;
        };
        
        this.activeUtterance.onerror = (e) => {
            console.error('Narrator error:', e);
            if (onEndCallback) onEndCallback();
            this.activeUtterance = null;
        };

        this.synth.speak(this.activeUtterance);
    }

    pause() {
        if (this.synth && this.synth.speaking && !this.synth.paused) {
            this.synth.pause();
        }
    }

    resume() {
        if (this.synth && this.synth.paused) {
            this.synth.resume();
        }
    }

    cancel() {
        if (this.synth) {
            this.synth.cancel();
            this.activeUtterance = null;
        }
    }

    isSpeaking() {
        return this.synth ? this.synth.speaking : false;
    }
}

export const narrator = new NarratorService();
