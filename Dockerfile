FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /source
COPY src/Orbital.Api/Orbital.Api.csproj src/Orbital.Api/
RUN dotnet restore src/Orbital.Api/Orbital.Api.csproj
COPY src/ src/
RUN dotnet publish src/Orbital.Api/Orbital.Api.csproj -c Release -o /out --no-restore /p:UseAppHost=false

FROM mcr.microsoft.com/dotnet/aspnet:8.0-bookworm-slim AS runtime
RUN groupadd --gid 16558 orbital && useradd --uid 16558 --gid orbital --create-home orbital
WORKDIR /app
COPY --from=build --chown=orbital:orbital /out ./
ENV ASPNETCORE_URLS=http://+:8080
EXPOSE 8080
USER orbital
ENTRYPOINT ["dotnet", "Orbital.Api.dll"]
