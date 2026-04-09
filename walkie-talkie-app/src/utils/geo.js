export function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371e3; // metres
    const phi1 = lat1 * Math.PI / 180;
    const phi2 = lat2 * Math.PI / 180;
    const deltaPhi = (lat2 - lat1) * Math.PI / 180;
    const deltaLambda = (lon2 - lon1) * Math.PI / 180;

    const a = Math.sin(deltaPhi / 2) * Math.sin(deltaPhi / 2) +
        Math.cos(phi1) * Math.cos(phi2) *
        Math.sin(deltaLambda / 2) * Math.sin(deltaLambda / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

    const distance = R * c;
    return distance;
}

export async function fetchWalkingRoute(coordinates) {
    if (!coordinates || coordinates.length < 2) return null;
    const coordString = coordinates.map(c => `${c.lng},${c.lat}`).join(';');
    const url = `https://router.project-osrm.org/route/v1/foot/${coordString}?overview=full&geometries=geojson&steps=true`;
    
    try {
        const res = await fetch(url);
        const data = await res.json();
        return data;
    } catch(e) {
        console.error("OSRM Routing Error:", e);
        return null;
    }
}
