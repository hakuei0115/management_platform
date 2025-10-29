import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { fakeLoginAPI } from "@/services/api";

export const useAuthStore = defineStore("auth", () => {
    const token = ref(localStorage.getItem("token") || "");
    const username = ref(localStorage.getItem("username") || "");

    const isLoggedIn = computed(() => !!token.value);

    async function login(user, pass) {
        const res = await fakeLoginAPI(user, pass);
        if (res.success) {
            token.value = res.token;
            username.value = res.username;
            localStorage.setItem("token", token.value);
            localStorage.setItem("username", username.value);
            return true;
        }
        return false;
    }

    function logout() {
        token.value = "";
        username.value = "";
        localStorage.removeItem("token");
        localStorage.removeItem("username");
    }

    return { token, username, isLoggedIn, login, logout };
});
