import type {
    BusinessDetails,
    BusinessSearchResult,
} from "../types/business";

const API_URL = "http://localhost:8080";

interface ApiError {
    detail?: string;
}

async function handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
        let message = `Erreur ${response.status}`;

        try {
            const error = (await response.json()) as ApiError;
            message = error.detail ?? message;
        } catch {
            // On garde le message par défaut
        }

        throw new Error(message);
    }

    return response.json() as Promise<T>;
}

export async function searchBusinesses(query: string) {
    const response = await fetch(`${API_URL}/businesses/search`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            query: query.trim(),
            max_results: 20,
        }),
    });

    return handleResponse<{ results: BusinessSearchResult[] }>(response);
}

export async function selectBusiness(placeId: string) {
    const response = await fetch(`${API_URL}/businesses/select`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ place_id: placeId }),
    });

    return handleResponse<{ business: BusinessDetails }>(response);
}