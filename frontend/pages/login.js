import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import { postLogin } from "../api/auth";

function LoginPage() {
    const router = useRouter();
    const [status, setStatus] = useState("loading");

    useEffect(() => {
        const autoLogin = async () => {
            const result = await postLogin({
                email: "ransivavakalapudi@gmail.com",  // Your test user
                password: "Siva&6262"
            });

            if (result.ok) {
                setStatus("done");
                router.replace("/"); // ✅ Redirect to home
            } else {
                setStatus("failed");
            }
        };

        autoLogin();
    }, [router]);

    if (status === "loading") {
        return <div>Logging in automatically...</div>;
    }

    return <div>Login failed. Please check credentials.</div>;
}

export default LoginPage;
