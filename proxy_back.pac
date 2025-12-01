function FindProxyForURL(url, host) {

    if (isPlainHostName(host) ||
        shExpMatch(host, "127.*") ||
        shExpMatch(host, "10.*") ||
        shExpMatch(host, "192.168.*")) {
        return "DIRECT";
    }

    if (shExpMatch(host, "*.local") || shExpMatch(host, "*.LOCAL") ||
        shExpMatch(host, "*.ru") || shExpMatch(host, "*.RU") ||
        shExpMatch(host, "*.рф") || shExpMatch(host, "*.РФ") ||
		shExpMatch(host, "vk.*") || shExpMatch(host, "VK.*") ||
        shExpMatch(host, "*yandex*") || shExpMatch(host, "*YANDEX*") ||
		shExpMatch(host, "*deepseek.*") || shExpMatch(host, "*DEEPSEEK.*")) {
        return "DIRECT";
    }

    return "SOCKS5 127.0.0.1:{port}";
}
