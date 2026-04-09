export function generateIntro(placeName) {
    const templates = [
        `Now that you've reached ${placeName}, let's talk about it.`,
        `Look closely—you're standing right near ${placeName}.`,
        `You've made it to ${placeName}. Here's what the locals know.`,
        `Welcome to ${placeName}. The history here is incredible.`,
        `Take a look around. This is ${placeName}, and it has quite a story.`
    ];
    const randomIndex = Math.floor(Math.random() * templates.length);
    return templates[randomIndex];
}
