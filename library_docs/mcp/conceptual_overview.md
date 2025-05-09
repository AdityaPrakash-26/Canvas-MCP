**What the MCP is**

The Model Context Protocol (MCP) is an open protocol designed to provide a standardized way for Large Language Model (LLM) applications to connect with external data sources, tools, and other resources. It allows LLM-based hosts (such as desktop applications, IDEs, or custom AI workflows) to seamlessly integrate with a variety of services and local or remote data. By using MCP, these hosts gain a consistent interface to discover, access, and interact with resources and functionalities offered by one or more servers.

**How it works**

MCP follows a client-server architecture:

- **MCP Hosts**: Applications that initiate connections and request capabilities, such as LLM-based interfaces or development environments.
- **MCP Clients**: Client components inside a host application that establish and maintain 1:1 connections with servers.
- **MCP Servers**: Separate lightweight programs or services that implement the MCP interface and expose capabilities. Each server might provide access to local files, databases, APIs, or specialized functionalities.

When a host application starts, it discovers and connects to configured MCP servers. Through a standardized handshake, the host and server negotiate protocol capabilities. When a user or the LLM within the host requests data or an action, the host identifies which MCP server can fulfill that need, sends a request over the MCP connection, and receives results back from the server.

**Key architectural aspects:**

1. **Server Discovery**: When the host (e.g., a desktop application) launches, it finds and connects to available MCP servers.
2. **Protocol Handshake**: They establish a communication session, agreeing on capabilities, protocols, and message formats.
3. **Interaction Flow**: The host sends requests for data or actions; the server processes these requests, interacts with local or remote resources, and returns structured results.
4. **Security**: MCP servers expose controlled capabilities and typically run locally, ensuring that sensitive data is not exposed arbitrarily. Resources and functionalities are accessed securely, and only within the defined capabilities of each server.

MCP uses messages in the form of requests, responses, and notifications. Requests expect responses, notifications do not, and errors are clearly reported. MCP supports multiple transport mechanisms (like standard input/output or HTTP-based SSE) and ensures that hosts and servers can exchange structured data efficiently.

**Tools in MCP**

Tools are a fundamental concept in MCP that enable servers to expose executable actions or operations to clients. While resources provide data, tools provide functionality. Through tools, LLMs (with human oversight) can perform actions that go beyond just reading data. For example, tools might allow running a command, calling an external API, or performing a calculation.

Key points about tools:

- **Model-Controlled Execution**: Tools are designed so that an AI model, once granted permission by a human, can invoke them. This means the model can integrate these tools into its workflow automatically.
- **Discovery and Invocation**: Clients can list all available tools from a server and understand their input parameters and capabilities. Tools are described by their names, descriptions, and input schemas. To use a tool, a client calls it with the appropriate parameters, and the server executes the operation and returns the results.
- **Flexibility**: Tools can represent many different kinds of actions, from interacting with local systems (e.g., running commands) to invoking remote services or performing complex data transformations.

**Resources in MCP**

Resources are another core concept. They represent data made available by the server. Unlike tools, which perform actions, resources provide static or dynamic content that can be read and used as context. Common examples include:

- Files and documents
- Database entries
- API responses transformed into a readable format
- Images, logs, or other content artifacts

Key points about resources:

- **Identification via URIs**: Every resource is identified by a unique URI. The URI can follow custom schemes defined by the server.
- **Types of Content**: Resources can be text-based (like source code, logs, or config files) or binary (like images, PDFs, or other non-text formats).
- **Discovery and Reading**: The client can list available resources, understand what each resource contains, and then request to read the content. Some servers may also support resource templates, allowing clients to request dynamic or parameterized resources.
- **Updates and Subscriptions**: MCP supports notifications when resource lists or contents change. Clients can subscribe to updates for specific resources to stay informed about changes over time.

**In summary:**

- MCP is a standardized, open protocol that enables LLM hosts to seamlessly integrate with a variety of servers.
- It defines a clear architecture of hosts, clients, and servers connected through a well-defined protocol.
- Tools in MCP allow the execution of actions and operations accessible to the model (with user permission).
- Resources in MCP represent data and context that can be provided to LLMs in a structured way.
- Together, tools and resources empower LLMs to be more context-aware and capable, while maintaining security, structure, and extensibility.
