import Chat from "../components/chat/Main";
import Layout from "../components/chat/Layout";
import { useDispatch } from "react-redux";
import { useEffect } from "react";
import { fetchCsrfTokenThunk } from "../redux/auth";
import { getServerSidePropsAuthHelper } from "../api/auth";

function Home({ isAuthenticated }) {
    const dispatch = useDispatch();

    useEffect(() => {
        dispatch(fetchCsrfTokenThunk());
    }, [dispatch]);

    return (
        <Layout title="Custom ChatGPT">
            <Chat />
        </Layout>
    );
}

// ✅ Use the always-auth helper for dev
export { getServerSidePropsAuthHelper as getServerSideProps };

export default Home;
