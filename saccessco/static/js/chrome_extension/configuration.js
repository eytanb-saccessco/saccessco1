const SACCESSCO_WEBSOCKET_URL = "ws://localhost:8000/ws/saccessco/ai/"
const SACCESSCO_USER_PROMPT_URL = "http://localhost:8000/saccessco/user_prompt/";
const SACCESSCO_PAGE_CHANGE_URL = "http://localhost:8000/saccessco/page_change/";
const TEST_PAGE_URL = "http://localhost:8000/test-page/";

const DEBUG = false;
const LANGUAGE = "en-US";
const ROLE = {
    User: "user",
    System: "system"
};

window.configuration = {
    SACCESSCO_WEBSOCKET_URL,
    SACCESSCO_USER_PROMPT_URL,
    SACCESSCO_PAGE_CHANGE_URL,
    TEST_PAGE_URL,
    DEBUG,
    ROLE,
    LANGUAGE
};
